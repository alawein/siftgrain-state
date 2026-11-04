import json
import os
from copy import deepcopy

import pytest

from siftgrain_state.cli import main
from siftgrain_state.contract import InputError, load_packet, validate
from siftgrain_state.core import check_packet, same_json
from siftgrain_state.report import render_html


def packet():
    return {
        "schema_version": 1,
        "as_of": "2026-10-04T12:00:00Z",
        "requirements": [
            {
                "id": "r",
                "subject": "alarm",
                "path": ["time"],
                "expected": "07:00",
                "observation_id": "o",
                "max_age_seconds": 120,
                "action_id": "a",
            }
        ],
        "actions": [{"id": "a", "status": "succeeded"}],
        "observations": [
            {
                "id": "o",
                "subject": "alarm",
                "observed_at": "2026-10-04T11:59:00Z",
                "state": {"time": "07:00"},
            }
        ],
    }


@pytest.mark.parametrize(
    "kind,status,outcome,action,reason",
    [
        ("clean", "confirmed", "confirmed", "confirmed", "expected value observed"),
        ("wrong", "contradicted", "contradicted", "confirmed", "different value observed"),
        ("failed", "contradicted", "confirmed", "contradicted", "expected value observed"),
        ("missing-action", "unobserved", "confirmed", "unobserved", "expected value observed"),
        ("unknown-action", "unobserved", "confirmed", "unobserved", "expected value observed"),
        ("no-action", "confirmed", "confirmed", "not_required", "expected value observed"),
        ("missing-observation", "unobserved", "unobserved", "confirmed", "missing observation"),
        ("stale", "unobserved", "unobserved", "confirmed", "stale observation"),
        ("future", "unobserved", "unobserved", "confirmed", "future observation"),
        ("subject", "unobserved", "unobserved", "confirmed", "subject mismatch"),
        ("path", "unobserved", "unobserved", "confirmed", "missing object path"),
        ("bool-number", "contradicted", "contradicted", "confirmed", "different value observed"),
    ],
)
def test_decision_matrix(kind, status, outcome, action, reason):
    p = packet()
    if kind == "wrong":
        p["observations"][0]["state"]["time"] = "07:30"
    if kind == "failed":
        p["actions"][0]["status"] = "failed"
    if kind == "missing-action":
        p["actions"] = []
    if kind == "unknown-action":
        p["actions"][0]["status"] = "unknown"
    if kind == "no-action":
        p["requirements"][0]["action_id"] = None
    if kind == "missing-observation":
        p["observations"] = []
    if kind == "stale":
        p["observations"][0]["observed_at"] = "2026-10-04T11:45:00Z"
    if kind == "future":
        p["observations"][0]["observed_at"] = "2026-10-04T12:00:01Z"
    if kind == "subject":
        p["observations"][0]["subject"] = "other"
    if kind == "path":
        p["observations"][0]["state"] = {}
    if kind == "bool-number":
        p["requirements"][0]["expected"] = True
        p["observations"][0]["state"]["time"] = 1
    result = check_packet(p)
    assert result["results"][0] == {
        "id": "r",
        "action": action,
        "outcome": outcome,
        "status": status,
        "reason": reason,
        "action_id": p["requirements"][0]["action_id"],
        "observation_id": "o",
    }
    assert result["exit_code"] == (0 if status == "confirmed" else 1)


def test_retry_reference_and_nested_types():
    p = packet()
    p["observations"][0]["state"]["time"] = "07:30"
    p["observations"].append(p["observations"][0] | {"id": "new", "state": {"time": "07:00"}})
    assert check_packet(p)["exit_code"] == 1
    reverse = deepcopy(p)
    reverse["observations"].reverse()
    assert check_packet(p) == check_packet(reverse)
    p["requirements"][0]["observation_id"] = "new"
    assert check_packet(p)["exit_code"] == 0
    assert not same_json({"a": [True]}, {"a": [1]})
    assert same_json({"a": [1, None]}, {"a": [1.0, None]})


@pytest.mark.parametrize(
    "change",
    [
        "duplicates",
        "no-requirements",
        "timezone",
        "negative-age",
        "bool-age",
        "unknown-field",
        "nonfinite",
        "path-empty",
        "depth",
    ],
)
def test_invalid_contract(change):
    p = packet()
    if change == "duplicates":
        p["observations"] *= 2
    if change == "no-requirements":
        p["requirements"] = []
    if change == "timezone":
        p["as_of"] = "2026-10-04T12:00:00"
    if change == "negative-age":
        p["requirements"][0]["max_age_seconds"] = -1
    if change == "bool-age":
        p["requirements"][0]["max_age_seconds"] = True
    if change == "unknown-field":
        p["extra"] = 1
    if change == "nonfinite":
        p["requirements"][0]["expected"] = float("nan")
    if change == "path-empty":
        p["requirements"][0]["path"] = []
    if change == "depth":
        value = None
        for _ in range(34):
            value = [value]
        p["requirements"][0]["expected"] = value
    with pytest.raises(InputError):
        validate(p)


@pytest.mark.parametrize(
    "raw",
    [b"\xff", b"\xef\xbb\xbf{}", b'{"id":1,"id":2}', b'{"a":NaN}', b"x" * (5 * 1024 * 1024 + 1)],
    ids=["utf8", "bom", "duplicate", "nan", "oversize"],
)
def test_bad_bytes(tmp_path, raw):
    source = tmp_path / "in.json"
    source.write_bytes(raw)
    with pytest.raises(InputError):
        load_packet(source)
    out = tmp_path / "out.json"
    out.write_text("KEEP")
    assert main([str(source), "--json", str(out), "--force"]) == 2
    assert out.read_text() == "KEEP"


def test_safe_outputs(tmp_path):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(packet()), encoding="utf-8")
    before = source.read_bytes()
    alias = tmp_path / "alias.json"
    os.link(source, alias)
    assert main([str(source), "--json", str(alias), "--force"]) == 2
    assert source.read_bytes() == before
    out = tmp_path / "out.json"
    out.write_text("KEEP")
    assert main([str(source), "--json", str(out)]) == 2
    alias2 = tmp_path / "alias2.json"
    os.link(out, alias2)
    assert main([str(source), "--json", str(out), "--html", str(alias2), "--force"]) == 2
    assert out.read_text() == "KEEP"
    assert main([str(source), "--json", str(out), "--force"]) == 0
    assert json.loads(out.read_text())["counts"]["confirmed"] == 1


def test_escaping_and_boundary():
    page = render_html({"reason": "<script>alert(1)</script>"})
    assert "<script>" not in page and "&lt;script&gt;" in page
    p = packet()
    p["requirements"][0]["max_age_seconds"] = 60
    assert check_packet(p)["exit_code"] == 0
    p["requirements"] = [p["requirements"][0] | {"id": str(i)} for i in range(10000)]
    assert check_packet(p)["counts"]["confirmed"] == 10000
    p["requirements"].append(p["requirements"][0] | {"id": "overflow"})
    with pytest.raises(InputError):
        validate(p)


@pytest.mark.parametrize("offset", ["+00:60", "+01:99", "+24:00", "-24:00"])
def test_invalid_timezone_offset(offset):
    p = packet()
    p["as_of"] = "2026-10-04T12:00:00" + offset
    with pytest.raises(InputError):
        validate(p)


def test_submicrosecond_future_and_stale():
    p = packet()
    p["requirements"][0]["max_age_seconds"] = 0
    p["observations"][0]["observed_at"] = "2026-10-04T12:00:00.0000001Z"
    assert check_packet(p)["results"][0]["reason"] == "future observation"
    p["observations"][0]["observed_at"] = "2026-10-04T11:59:59.9999999Z"
    assert check_packet(p)["results"][0]["reason"] == "stale observation"
