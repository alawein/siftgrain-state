import json

import pytest
from test_checks_v2 import baseline_packet, v2
from test_signatures import signed_packet

from siftgrain_state.cli import main
from siftgrain_state.contract import InputError, validate
from siftgrain_state.core import check_packet


@pytest.mark.parametrize(
    "expected",
    [
        {},
        {"min": True},
        {"max": "3"},
        {"min": 2, "max": 1},
        {"min_inclusive": True},
        {"min": 1, "max_inclusive": False},
        {"min": 1, "extra": 2},
    ],
)
def test_bad_range_contract(expected):
    with pytest.raises(InputError):
        validate(v2("range", expected, 1))


def test_large_integer_range_without_float_conversion():
    assert check_packet(v2("range", {"min": 10**400}, 10**400))["exit_code"] == 0
    assert check_packet(v2("range", {"max": 1.0}, 10**400))["exit_code"] == 1


@pytest.mark.parametrize("change", ["boolean", "duplicate", "extra", "wrong_type", "conflicting"])
def test_bad_v2_contract(change):
    p = baseline_packet()
    if change == "boolean":
        p["requirements"][0]["requires_change"] = 1
    elif change == "duplicate":
        p["baselines"] *= 2
    elif change == "extra":
        p["baselines"][0]["unknown"] = True
    elif change == "wrong_type":
        p["baselines"] = {}
    else:
        p["requirements"][0]["check"] = "unchanged"
    with pytest.raises(InputError):
        validate(p)


def test_cli_local_public_keys_and_input_identity(tmp_path):
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    p, _ = signed_packet()
    p["require_signatures"] = True
    source, keys, target = (tmp_path / name for name in ("packet.json", "keys.json", "report.json"))
    source.write_text(json.dumps(p))
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    keys.write_text(json.dumps({"fixture": base64.b64encode(raw).decode()}))
    assert main([str(source), "--public-keys", str(keys), "--json", str(target)]) == 0
    before = keys.read_bytes()
    assert main([str(source), "--public-keys", str(keys), "--json", str(keys), "--force"]) == 2
    assert keys.read_bytes() == before
    keys.write_text('{"fixture": "bad"}')
    before = target.read_bytes()
    assert main([str(source), "--public-keys", str(keys), "--json", str(target), "--force"]) == 2
    assert target.read_bytes() == before


def test_v1_rejects_v2_extensions():
    p = v2()
    p["schema_version"] = 1
    with pytest.raises(InputError):
        validate(p)


def test_oversized_regex_value_and_invalid_class():
    assert check_packet(v2("regex", "^a$", "a" * 5000))["exit_code"] == 1
    with pytest.raises(InputError):
        validate(v2("regex", "^[Z-A]$"))
