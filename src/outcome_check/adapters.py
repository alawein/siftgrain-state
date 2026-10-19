"""Explicit, offline projections. Scores and agent claims never become observations."""

from copy import deepcopy
from typing import Any

from outcome_check.contract import require, validate


def convert(
    kind: str,
    record: dict,
    *,
    as_of: str,
    observed_at: str,
    max_age_seconds: int,
    expected: dict | None = None,
    baseline_at: str | None = None,
    requires_change: bool = False,
) -> dict:
    """Convert one record with caller-supplied clocks and goals; never run its tools.

    tau accepts explicit initial_state/final_state snapshots. Inspect accepts
    store.outcome_state and store.baseline_state from a caller-owned collector.
    SWE-bench accepts a per-instance resolved Boolean from its native test report.
    Missing snapshots remain missing. No timestamp, subject or goal is inferred.
    """
    require(type(record) is dict, "adapter record must be an object")
    require(type(requires_change) is bool, "requires_change must be Boolean")
    state: Any
    before: Any
    if kind == "swebench":
        if "instance_id" not in record and len(record) == 1:
            native_id, native = next(iter(record.items()))
            require(type(native) is dict, "native per-instance report must be an object")
            require(
                "instance_id" not in native
                or (
                    type(native["instance_id"]) is type(native_id)
                    and native["instance_id"] == native_id
                ),
                "conflicting instance_id in native per-instance report",
            )
            record = native | {"instance_id": native_id}
        subject = record.get("instance_id")
        require(type(record.get("resolved")) is bool, "resolved Boolean required")
        state = {"resolved": record["resolved"]}
        before = None
        require(expected is None, "SWE-bench goal is resolved=true")
        expected = {"resolved": True}
    elif kind == "tau":
        subject = record.get("task_id")
        for key in ("final_state", "initial_state"):
            require(key not in record or type(record[key]) is dict, f"{key} must be an object")
        state, before = record.get("final_state"), record.get("initial_state")
    elif kind == "inspect":
        subject = record.get("id")
        store = record.get("store", {})
        require(type(store) is dict, "Inspect store must be an object")
        for key in ("outcome_state", "baseline_state"):
            require(
                key not in store or type(store[key]) is dict,
                f"Inspect {key} must be an object",
            )
        state, before = store.get("outcome_state"), store.get("baseline_state")
    else:
        raise ValueError("adapter must be tau, swebench or inspect")
    require(type(subject) in (str, int) and bool(str(subject).strip()), "explicit subject required")
    require(type(expected) is dict and bool(expected), "explicit nonempty goal object required")
    require(state is None or type(state) is dict, "final state must be an object")
    require(before is None or type(before) is dict, "baseline state must be an object")
    require(before is None or baseline_at is not None, "baseline_at required with baseline state")
    subject = str(subject)
    assert expected is not None
    packet: dict[str, Any] = {
        "schema_version": 3,
        "as_of": as_of,
        "actions": [],
        "baselines": [],
        "observations": [],
        "requirements": [],
    }
    if state is not None:
        packet["observations"].append(
            {
                "id": "final",
                "subject": subject,
                "observed_at": observed_at,
                "state": deepcopy(state),
            }
        )
    if before is not None:
        packet["baselines"].append(
            {
                "id": "before",
                "subject": subject,
                "observed_at": baseline_at,
                "state": deepcopy(before),
            }
        )
    for key, value in sorted(expected.items()):
        row = {
            "id": key,
            "subject": subject,
            "path": [key],
            "expected": deepcopy(value),
            "observation_id": "final",
            "max_age_seconds": max_age_seconds,
            "action_id": None,
        }
        if requires_change:
            row.update(baseline_id="before", requires_change=True)
        packet["requirements"].append(row)
    validate(packet)
    return packet
