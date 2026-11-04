"""Local verification interface and restricted canonical JSON for observation signatures."""

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from siftgrain_state.contract import InputError, require, unique_pairs


class SignatureVerifier(Protocol):
    def verify(self, algorithm: str, key_id: str, signature: bytes, payload: bytes) -> bool: ...


def canonical_json(value: object) -> bytes:
    """RFC 8785 subset: no floats, safe integers, no lone surrogates; UTF-16 key order."""

    def normalize(item):
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            require(abs(item) <= 9007199254740991, "canonical integer outside safe range")
            return item
        if type(item) is str:
            try:
                item.encode("utf-16-be")
            except UnicodeError as exc:
                raise InputError("canonical string contains lone surrogate") from exc
            return item
        if type(item) is list:
            return [normalize(child) for child in item]
        require(type(item) is dict, "canonical JSON supports no floats")
        for key in item:
            require(type(key) is str, "canonical keys must be strings")
            normalize(key)
        return {
            key: normalize(item[key])
            for key in sorted(item, key=lambda key: key.encode("utf-16-be"))
        }

    return json.dumps(
        normalize(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def signing_payload(observation: dict) -> bytes:
    signature = observation["signature"]
    profile = signature.get("canonicalization")
    require(profile in (None, "RFC8785"), "unsupported signature canonicalization")
    require(signature["algorithm"] == "Ed25519", "unsupported signature algorithm")
    metadata = {"algorithm": signature["algorithm"], "key_id": signature["key_id"]}
    serializer = canonical_json
    if profile is not None:
        from siftgrain_state.canonical import canonicalize

        metadata["canonicalization"] = profile
        serializer = canonicalize
    return serializer(
        {key: value for key, value in observation.items() if key != "signature"} | metadata
    )


def signature_status(observation: dict, verifier: SignatureVerifier | None) -> str:
    if "signature" not in observation:
        return "unsigned"
    try:
        signature = observation["signature"]
        raw = base64.b64decode(signature["signature"], validate=True)
        require(len(raw) == 64, "invalid Ed25519 signature length")
        payload = signing_payload(observation)
        if verifier is None:
            return "unverified"
        return (
            "verified"
            if verifier.verify(signature["algorithm"], signature["key_id"], raw, payload)
            else "invalid"
        )
    except (ValueError, TypeError, KeyError, UnicodeError):
        return "invalid"


class Ed25519Verifier:
    """Only caller-supplied local raw public keys are trusted. Never fetches a key."""

    def __init__(self, keys: Mapping[str, bytes]):
        self.keys = dict(keys)

    def verify(self, algorithm: str, key_id: str, signature: bytes, payload: bytes) -> bool:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        if algorithm != "Ed25519" or key_id not in self.keys:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(self.keys[key_id]).verify(signature, payload)
        except (InvalidSignature, ValueError):
            return False
        return True


def sign_observation(
    observation: dict, key_id: str, private_key: bytes, *, canonicalization: str | None = None
) -> dict:
    """Optional extra; returns a new observation, never writes private keys."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    result = observation | {
        "signature": {"algorithm": "Ed25519", "key_id": key_id, "signature": ""}
    }
    if canonicalization is not None:
        result["signature"]["canonicalization"] = canonicalization
    signature = Ed25519PrivateKey.from_private_bytes(private_key).sign(signing_payload(result))
    result["signature"]["signature"] = base64.b64encode(signature).decode("ascii")
    return result


def load_public_keys(path: Path) -> Ed25519Verifier:
    with path.open("rb") as stream:
        raw = stream.read(5 * 1024 * 1024 + 1)
    require(len(raw) <= 5 * 1024 * 1024, "public keys input exceeds 5 MiB")
    keys = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    require(type(keys) is dict and len(keys) <= 10000, "public keys must be an object")
    decoded = {}
    for key_id, encoded in keys.items():
        require(
            type(key_id) is str and bool(key_id.strip()) and len(key_id) <= 200, "invalid key ID"
        )
        require(type(encoded) is str, "public key must be base64 string")
        assert isinstance(encoded, str)
        key = base64.b64decode(encoded, validate=True)
        require(len(key) == 32, "Ed25519 public key must be 32 bytes")
        decoded[key_id] = key
    return Ed25519Verifier(decoded)
