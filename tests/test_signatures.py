import base64
from copy import deepcopy

import pytest
from test_checks_v2 import baseline_packet, v2

from siftgrain_state.contract import InputError
from siftgrain_state.core import check_packet
from siftgrain_state.signatures import (
    Ed25519Verifier,
    canonical_json,
    sign_observation,
    signature_status,
)


def test_canonical_vectors_and_utf16_key_order():
    assert (
        canonical_json({"b": [True, None], "a": "\n€"})
        == b'{"a":"\\n\xe2\x82\xac","b":[true,null]}'
    )
    assert canonical_json({"\ue000": 1, "\U0001f600": 2}) == '{"😀":2,"\ue000":1}'.encode()
    assert canonical_json({"n": 9007199254740991}) == b'{"n":9007199254740991}'


@pytest.mark.parametrize("value", [1.0, 9007199254740992, "\ud800", {"\udfff": 1}])
def test_canonical_unsupported_values_rejected(value):
    with pytest.raises(InputError):
        canonical_json(value)


def signed_packet():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    p = v2()
    p["observations"][0] = sign_observation(p["observations"][0], "fixture", bytes(range(32)))
    return p, Ed25519Verifier({"fixture": public})


def test_signatures_verified_tamper_and_missing():
    p, verifier = signed_packet()
    p["require_signatures"] = True
    report = check_packet(p, verifier)
    assert report["exit_code"] == 0
    assert report["results"][0]["signature"] == "verified"
    unsigned = deepcopy(p)
    unsigned["observations"][0].pop("signature")
    assert check_packet(unsigned, verifier)["exit_code"] == 1
    assert check_packet(p)["exit_code"] == 1
    p["observations"][0]["state"]["unused"] = "tampered"
    assert check_packet(p, verifier)["results"][0]["signature"] == "invalid"
    assert check_packet(p, verifier)["exit_code"] == 1


def test_unsigned_nonfailure_and_unverified_label():
    assert check_packet(v2())["results"][0]["signature"] == "unsigned"
    p, _ = signed_packet()
    assert check_packet(p)["results"][0]["signature"] == "unverified"
    assert check_packet(p)["exit_code"] == 0
    assert check_packet(p, Ed25519Verifier({}))["exit_code"] == 1


@pytest.mark.parametrize("value", ["", "not-base64!", base64.b64encode(b"x" * 63).decode()])
def test_invalid_signature_never_confirms(value):
    p, verifier = signed_packet()
    p["observations"][0]["signature"]["signature"] = value
    assert check_packet(p, verifier)["exit_code"] == 1


def test_required_baseline_signature():
    p = baseline_packet(before="08:00")
    p["require_signatures"] = True
    signed, verifier = signed_packet()
    p["observations"] = signed["observations"]
    assert check_packet(p, verifier)["exit_code"] == 1
    p["baselines"][0] = sign_observation(p["baselines"][0], "fixture", bytes(range(32)))
    assert check_packet(p, verifier)["exit_code"] == 0
    assert signature_status(p["baselines"][0], verifier) == "verified"


def test_verifier_runs_once_per_observation_and_report_agrees():
    p, real = signed_packet()

    class Once:
        calls = 0

        def verify(self, *args):
            self.calls += 1
            assert self.calls == 1
            return real.verify(*args)

    verifier = Once()
    p["require_signatures"] = True
    report = check_packet(p, verifier)
    assert report["exit_code"] == 0
    assert report["results"][0]["signature"] == "verified"


def test_v3_signing_profile_and_signed_migration():
    from siftgrain_state.contract import migrate_to_v3
    from siftgrain_state.signatures import signing_payload

    p, verifier = signed_packet()
    with pytest.raises(InputError, match="re-sign"):
        migrate_to_v3(p)
    p = migrate_to_v3(v2(expected=1.5, value=1.5))
    p["observations"][0] = sign_observation(
        p["observations"][0], "fixture", bytes(range(32)), canonicalization="RFC8785"
    )
    p["require_signatures"] = True
    assert b'"canonicalization":"RFC8785"' in signing_payload(p["observations"][0])
    assert check_packet(p, verifier)["exit_code"] == 0
    assert check_packet(p)["exit_code"] == 1
    assert p["schema_version"] == 3


@pytest.mark.parametrize(
    "change", ["profile", "remove_profile", "algorithm", "key_id", "value", "timestamp", "subject"]
)
def test_v3_tampering(change):
    from siftgrain_state.contract import migrate_to_v3

    _, verifier = signed_packet()
    p = migrate_to_v3(v2(expected=1.5, value=1.5))
    obs = sign_observation(
        p["observations"][0], "fixture", bytes(range(32)), canonicalization="RFC8785"
    )
    p["observations"][0] = obs
    if change == "profile":
        obs["signature"]["canonicalization"] = "UNKNOWN"
    elif change == "remove_profile":
        obs["signature"].pop("canonicalization")
    elif change == "algorithm":
        obs["signature"]["algorithm"] = "UNKNOWN"
    elif change == "key_id":
        obs["signature"]["key_id"] = "another"
    elif change == "value":
        obs["state"]["time"] = 1.75
    elif change == "timestamp":
        obs["observed_at"] = "2026-10-04T11:59:01Z"
    else:
        obs["subject"] = "changed"
    if change in ("profile", "remove_profile", "algorithm"):
        with pytest.raises(InputError):
            check_packet(p, verifier)
    else:
        assert signature_status(obs, verifier) == "invalid"
        assert check_packet(p, verifier)["exit_code"] == 1


def test_v2_cannot_opt_in_to_float_profile():
    p, verifier = signed_packet()
    p["observations"][0] = sign_observation(
        p["observations"][0], "fixture", bytes(range(32)), canonicalization="RFC8785"
    )
    with pytest.raises(InputError):
        check_packet(p, verifier)
    with pytest.raises(InputError):
        sign_observation(
            p["observations"][0], "fixture", bytes(range(32)), canonicalization="unknown"
        )


def test_unsigned_migrations_preserve_source():
    from test_outcomes import packet

    from siftgrain_state.contract import migrate_to_v3

    for source in (packet(), v2()):
        before = deepcopy(source)
        migrated = migrate_to_v3(source)
        assert migrated["schema_version"] == 3
        assert check_packet(migrated)["exit_code"] == check_packet(source)["exit_code"]
        migrated["observations"][0]["state"]["x"] = 1
        assert source == before
