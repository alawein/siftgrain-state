from copy import deepcopy

import pytest
from test_outcomes import packet

from siftgrain_state.contract import InputError, validate
from siftgrain_state.core import check_packet


def v2(check="equal", expected="07:00", value="07:00"):
    p = packet()
    p["schema_version"] = 2
    p["baselines"] = []
    p["requirements"][0].update(check=check, expected=expected)
    p["observations"][0]["state"]["time"] = value
    return p


@pytest.mark.parametrize(
    "check,expected,value,status",
    [
        ("equal", True, 1, "contradicted"),
        ("range", {"min": 1, "max": 3}, 1, "confirmed"),
        ("range", {"min": 1, "min_inclusive": False}, 1, "contradicted"),
        ("range", {"max": 3, "max_inclusive": False}, 3, "contradicted"),
        ("range", {"min": 1}, True, "contradicted"),
        ("contains", True, [1], "contradicted"),
        ("contains", {"x": [1]}, [{"x": [1.0]}], "confirmed"),
        ("contains", 1, "1", "contradicted"),
        ("regex", "^[A-Z]{2}[0-9]{2}$", "AB12", "confirmed"),
        ("regex", "^ok$", "ok\n", "contradicted"),
    ],
)
def test_checks(check, expected, value, status):
    assert check_packet(v2(check, expected, value))["results"][0]["status"] == status


@pytest.mark.parametrize(
    "pattern", ["(a+)+$", "^a|b$", "^a.*$", "^a+$", "^a{1,9999}$", "^a\\1$", "abc"]
)
def test_reject_complex_regex(pattern):
    with pytest.raises(InputError):
        validate(v2("regex", pattern))


def baseline_packet(check="equal", before="07:00", after="07:00"):
    p = v2(check, "07:00", after)
    p["baselines"] = [
        deepcopy(p["observations"][0])
        | {"id": "before", "observed_at": "2026-10-04T11:58:00Z", "state": {"time": before}}
    ]
    p["requirements"][0].update(baseline_id="before", requires_change=True)
    return p


def test_do_nothing_agent_unconfirmed():
    p = baseline_packet()
    row = check_packet(p)["results"][0]
    assert row["status"] == "unconfirmed"
    assert row["reason"] == "no observed change"
    assert check_packet(p)["counts"]["unconfirmed"] == 1
    p["baselines"][0]["state"]["time"] = "08:00"
    assert check_packet(p)["exit_code"] == 0


@pytest.mark.parametrize(
    "check,before,after,status",
    [
        ("unchanged", "07:00", "07:00", "confirmed"),
        ("unchanged", "08:00", "07:00", "contradicted"),
        ("changed_from_baseline", "07:00", "07:00", "contradicted"),
        ("changed_from_baseline", "08:00", "07:00", "confirmed"),
    ],
)
def test_baseline_checks(check, before, after, status):
    p = baseline_packet(check, before, after)
    p["requirements"][0]["requires_change"] = False
    assert check_packet(p)["results"][0]["status"] == status


@pytest.mark.parametrize("change", ["missing", "subject", "future", "path", "same_time"])
def test_invalid_baseline_never_confirms(change):
    p = baseline_packet(before="08:00")
    if change == "missing":
        p["baselines"] = []
    elif change == "subject":
        p["baselines"][0]["subject"] = "other"
    elif change == "future":
        p["baselines"][0]["observed_at"] = "2026-10-04T12:01:00Z"
    elif change == "same_time":
        p["baselines"][0]["observed_at"] = p["observations"][0]["observed_at"]
    else:
        p["baselines"][0]["state"] = {}
    assert check_packet(p)["exit_code"] == 1


@pytest.mark.parametrize("check", ["unchanged", "changed_from_baseline"])
def test_baseline_id_is_explicit(check):
    with pytest.raises(InputError):
        validate(v2(check))
