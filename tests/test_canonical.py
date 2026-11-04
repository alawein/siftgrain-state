import json
import math
import random
import struct
from pathlib import Path

import pytest
import rfc8785
from hypothesis import given, settings
from hypothesis import strategies as st

from siftgrain_state import signatures
from siftgrain_state.contract import InputError


def jcs(value):
    from siftgrain_state.canonical import canonicalize

    return canonicalize(value)


# RFC 8785 Appendix B, July 2020. Hex is the exact binary64 input.
VECTORS = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


@pytest.mark.parametrize("bits,expected", VECTORS)
def test_official_numeric_vectors(bits, expected):
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    assert jcs(value) == expected.encode() == rfc8785.dumps(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        (1.0, b"1"),
        (-0.0, b"0"),
        (1e-7, b"1e-7"),
        (1e-6, b"0.000001"),
        (1e20, b"100000000000000000000"),
        (1e21, b"1e+21"),
    ],
)
def test_ecmascript_thresholds(value, expected):
    assert jcs(value) == expected


def test_seeded_binary64_reference_crosscheck():
    rng = random.Random(8785)
    checked = 0
    for _ in range(20000):
        value = struct.unpack(">d", rng.getrandbits(64).to_bytes(8, "big"))[0]
        if math.isfinite(value):
            assert jcs(value) == rfc8785.dumps(value)
            checked += 1
    assert checked > 19900


@given(st.floats(allow_nan=False, allow_infinity=False, width=64))
@settings(max_examples=1000, derandomize=True)
def test_finite_reference_and_roundtrip(value):
    encoded = jcs(value)
    assert encoded == rfc8785.dumps(value)
    assert float(encoded) == value


def test_unicode_keys_nested_arrays_and_escaping():
    value = {"\ue000": 1, "\U0001f600": [{"z": 1.0, "a": '\x00\b\t\n\f\r\\"/€'}]}
    assert jcs(value) == rfc8785.dumps(value)
    assert jcs({"\ue000": 1, "\U0001f600": 2}) == '{"😀":2,"\ue000":1}'.encode()
    assert jcs("e\u0301") != jcs("é")


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        -float("inf"),
        "\ud800",
        {"\udfff": 1},
        {1: 2},
        (1,),
        9007199254740993,
        10**400,
    ],
)
def test_unsupported_values_fail(value):
    with pytest.raises(InputError):
        jcs(value)


def test_exactly_representable_integers_use_binary64_rendering():
    assert jcs(2**68) == b"295147905179352830000"


def test_legacy_payload_frozen():
    packet = json.loads(Path("examples/signed-v2.packet.json").read_text())
    observation = packet["observations"][0]
    expected = (
        b'{"algorithm":"Ed25519","id":"fresh","key_id":"synthetic-demo",'
        b'"observed_at":"2026-10-04T11:59:00Z",'
        b'"state":{"enabled":true,"time":"07:30"},"subject":"alarm-device"}'
    )
    assert signatures.signing_payload(observation) == expected
    verifier = signatures.load_public_keys(Path("examples/public-keys.json"))
    assert signatures.signature_status(observation, verifier) == "verified"
    for value in [1.0, -0.0, 2**53]:
        with pytest.raises(InputError):
            signatures.canonical_json(value)
