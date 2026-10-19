import io
import json
from copy import deepcopy

import pytest

from outcome_check.adapters import convert
from outcome_check.contract import InputError
from outcome_check.core import check_packet
from outcome_check.mcp import serve


def source():
    return {"instance_id": "x", "resolved": True}


def options():
    return dict(
        as_of="2026-10-13T12:00:00Z", observed_at="2026-10-13T11:59:00Z", max_age_seconds=60
    )


def test_swe_result_is_supplied_state_not_patch_execution():
    data = source()
    before = deepcopy(data)
    p = convert("swebench", data, **options())
    assert check_packet(p)["counts"]["confirmed"] == 1
    assert p["actions"] == []
    assert data == before


def test_swe_wrapper_rejects_conflicting_identity_without_mutation():
    for nested_id in ("another-instance", None, 1):
        data = {"x": {"instance_id": nested_id, "resolved": True}}
        before = deepcopy(data)
        with pytest.raises(InputError, match="conflicting instance_id"):
            convert("swebench", data, **options())
        assert data == before


def test_swe_wrapper_preserves_matching_explicit_identity():
    data = {"x": {"instance_id": "x", "resolved": True}}
    before = deepcopy(data)
    packet = convert("swebench", data, **options())
    assert packet["observations"][0]["subject"] == "x"
    assert check_packet(packet)["counts"]["confirmed"] == 1
    assert data == before


@pytest.mark.parametrize(
    "bad", [True, [], {}, {"instance_id": "x"}, {"instance_id": "x", "resolved": 1}]
)
def test_swe_malformed_rows_never_drop(bad):
    with pytest.raises(InputError):
        convert("swebench", bad, **options())


def test_inspect_reward_is_not_observation():
    p = convert(
        "inspect",
        {"id": "x", "scores": {"a": {"value": "C"}}, "store": {}},
        expected={"refund": True},
        **options(),
    )
    assert check_packet(p)["counts"]["unobserved"] == 1


def test_tau_final_state_and_baseline_defeat_noop():
    p = convert(
        "tau",
        {"task_id": 1, "final_state": {"refund": True}, "initial_state": {"refund": True}},
        expected={"refund": True},
        baseline_at="2026-10-13T11:58:00Z",
        requires_change=True,
        **options(),
    )
    assert check_packet(p)["counts"]["unconfirmed"] == 1


def test_tau_missing_final_is_unobserved_even_with_reward():
    p = convert("tau", {"task_id": 1, "reward": 1}, expected={"refund": True}, **options())
    assert check_packet(p)["counts"]["unobserved"] == 1


@pytest.mark.parametrize(
    ("kind", "record", "baseline_at", "requires_change"),
    [
        ("tau", {"task_id": "x", "final_state": None}, None, False),
        (
            "tau",
            {"task_id": "x", "final_state": {"refund": True}, "initial_state": None},
            "2026-10-13T11:58:00Z",
            True,
        ),
        ("inspect", {"id": "x", "store": {"outcome_state": None}}, None, False),
        (
            "inspect",
            {
                "id": "x",
                "store": {"outcome_state": {"refund": True}, "baseline_state": None},
            },
            "2026-10-13T11:58:00Z",
            True,
        ),
    ],
)
def test_explicit_null_snapshots_are_rejected_without_mutating_input(
    kind, record, baseline_at, requires_change
):
    data = deepcopy(record)
    with pytest.raises(InputError):
        convert(
            kind,
            data,
            expected={"refund": True},
            baseline_at=baseline_at,
            requires_change=requires_change,
            **options(),
        )
    assert data == record


def test_mcp_readonly_roundtrip_and_errors():
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "check",
                "arguments": {"packet": convert("swebench", source(), **options())},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "check", "arguments": {"path": "secret"}},
        },
    ]
    output = io.StringIO()
    serve(io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n"), output)
    rows = [json.loads(r) for r in output.getvalue().splitlines()]
    assert len(rows) == 4
    assert rows[1]["result"]["tools"][0]["annotations"]["readOnlyHint"] is True
    assert rows[2]["result"]["structuredContent"]["counts"]["confirmed"] == 1
    assert rows[3]["result"]["isError"] is True


def test_swe_native_per_instance_report():
    p = convert(
        "swebench", {"x": {"resolved": True, "patch_successfully_applied": True}}, **options()
    )
    assert p["requirements"][0]["subject"] == "x"
    assert check_packet(p)["counts"]["confirmed"] == 1
