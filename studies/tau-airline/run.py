"""Offline projections of supplied final reservation responses, never tool execution."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from siftgrain_state.core import check_packet

SOURCE_SHA256 = "e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa"
FIELDS = {
    "book_reservation": (
        "user_id",
        "origin",
        "destination",
        "flight_type",
        "cabin",
        "flights",
        "passengers",
        "total_baggages",
        "nonfree_baggages",
        "insurance",
    ),
    "update_reservation_flights": ("cabin", "flights"),
    "update_reservation_passengers": ("passengers",),
    "update_reservation_baggages": ("total_baggages", "nonfree_baggages"),
    "cancel_reservation": ("status",),
}


def state_events(trajectory: list[dict]) -> list[tuple[int, str, dict]]:
    events = []
    for index, message in enumerate(trajectory):
        if message.get("role") != "tool":
            continue
        try:
            state = json.loads(message.get("content", ""))
        except (TypeError, ValueError):
            continue
        if type(state) is dict and "reservation_id" in state and "error" not in state:
            events.append((index, message.get("name", ""), state))
    return events


def project(state: dict, key: str):
    value = state.get(key)
    if key == "flights" and type(value) is list:
        return [
            {"flight_number": row.get("flight_number"), "date": row.get("date")} for row in value
        ]
    return value


def evaluate(record: dict) -> dict:
    events = state_events(record["traj"])
    # Later explicit mutations override earlier expected fields for the same entity.
    goals: dict[str, dict] = {}
    for action in record["info"]["task"]["actions"]:
        name, kwargs = action["name"], action["kwargs"]
        if name not in FIELDS:
            continue
        entity = kwargs.get("reservation_id")
        if entity is None and name == "book_reservation":
            matches = [
                state["reservation_id"]
                for _, tool, state in events
                if tool == name and state.get("user_id") == kwargs.get("user_id")
            ]
            entity = matches[-1] if matches else "missing-booking-observation"
        if entity is None:
            continue
        goal = goals.setdefault(entity, {})
        for key in FIELDS[name]:
            if name == "cancel_reservation":
                goal[key] = "cancelled"
            elif key in kwargs:
                goal[key] = project(kwargs, key)
    packet = {
        "schema_version": 2,
        "as_of": "2026-10-08T12:00:00Z",
        "actions": [],
        "observations": [],
        "baselines": [],
        "requirements": [],
    }
    for entity, goal in sorted(goals.items()):
        observed = [state for _, _, state in events if state["reservation_id"] == entity]
        if observed:
            packet["observations"].append(
                {
                    "id": entity,
                    "subject": entity,
                    "observed_at": "2026-10-08T12:00:00Z",
                    "state": {
                        key: project(observed[-1], key) for key in goal if key in observed[-1]
                    },
                }
            )
        for key, value in sorted(goal.items()):
            packet["requirements"].append(
                {
                    "id": f"{entity}:{key}",
                    "subject": entity,
                    "path": [key],
                    "expected": value,
                    "observation_id": entity,
                    "max_age_seconds": 0,
                    "action_id": None,
                }
            )
    if not packet["requirements"]:
        # Missing goal/final DB is explicitly unobserved, never substituted with reward/hash.
        packet["requirements"].append(
            {
                "id": "full-goal-unavailable",
                "subject": "task",
                "path": ["full_goal"],
                "expected": None,
                "observation_id": "not-supplied",
                "max_age_seconds": 0,
                "action_id": None,
            }
        )
    report = check_packet(packet)
    statuses = {row["status"] for row in report["results"]}
    classification = (
        "contradicted"
        if "contradicted" in statuses
        else ("unobserved" if "unobserved" in statuses else "confirmed")
    )
    # Separate sensitivity diagnostic on explicit first/last logged reservation snapshots.
    # It is not a task-success judgment: legitimate refusal may require no state change.
    no_change = 0
    for entity in sorted({state["reservation_id"] for _, _, state in events}):
        selected = [
            (index, tool, state)
            for index, tool, state in events
            if state["reservation_id"] == entity
        ]
        first_index, first_tool, first = selected[0]
        last_index, _, last = selected[-1]
        # A pre-mutation lookup supplies the baseline. A single lookup supplies no
        # post-action observation, so cannot be reused as both snapshots.
        mutation_indices = [i for i, tool, _ in selected if tool in FIELDS]
        if first_tool != "get_reservation_details" or first_index == last_index:
            continue
        if mutation_indices and first_index >= min(mutation_indices):
            continue
        sensitivity = {
            "schema_version": 2,
            "as_of": "2026-10-08T12:00:00Z",
            "actions": [],
            "observations": [
                {
                    "id": "after",
                    "subject": entity,
                    "observed_at": "2026-10-08T12:00:00Z",
                    "state": {"reservation": last},
                }
            ],
            "baselines": [
                {
                    "id": "before",
                    "subject": entity,
                    "observed_at": "2026-10-08T11:59:59Z",
                    "state": {"reservation": first},
                }
            ],
            "requirements": [
                {
                    "id": "sensitivity",
                    "subject": entity,
                    "path": ["reservation"],
                    "expected": last,
                    "observation_id": "after",
                    "baseline_id": "before",
                    "requires_change": True,
                    "max_age_seconds": 0,
                    "action_id": None,
                }
            ],
        }
        no_change += check_packet(sensitivity)["counts"]["unconfirmed"]
    return {
        "task_id": record["task_id"],
        "upstream_reward": record["reward"],
        "projected_status": classification,
        "no_change_sensitivity_flags": no_change,
        "mapped_requirements": len(packet["requirements"]),
        "final_reservation_observations": len(packet["observations"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        parser.error("source checksum differs from pinned public trajectories")
    source = json.loads(raw)

    def run_rows():
        return [
            {"source_index": index, **evaluate(record)}
            for index, record in enumerate(source)
            if record["reward"] == 1
        ]

    rows = run_rows()
    assert rows == run_rows()
    result = {
        "source_sha256": SOURCE_SHA256,
        "trajectories_in_source": len(source),
        "upstream_successes": len(rows),
        "projected_counts": dict(sorted(Counter(row["projected_status"] for row in rows).items())),
        "successes_with_no_change_sensitivity_flag": sum(
            row["no_change_sensitivity_flags"] > 0 for row in rows
        ),
        "full_database_and_goal_recheck": "unobserved for all: complete snapshots not supplied",
        "full_database_success_counts": {
            "confirmed": 0,
            "contradicted": 0,
            "unobserved": len(rows),
        },
        "clock_policy": "Fixed study times encode relative log order, not collection freshness.",
        "rows": rows,
    }
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print("PASS: offline trajectory projection; full-state limitation recorded")


if __name__ == "__main__":
    main()
