"""Offline full-state protocol and pinned tau archive missing-input inventory."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from siftgrain_state.contract import (
    fields,
    identifier,
    json_value,
    require,
    timestamp,
    unique_pairs,
)
from siftgrain_state.core import check_packet

SOURCE_SHA256 = "e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa"
SOURCE = "https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/historical_trajectories/gpt-4o-airline.json"
STATUSES = ("confirmed", "contradicted", "unobserved", "unconfirmed")


def evaluate(record: dict) -> dict:
    """Compare the entire supplied database, plus each explicit mutation target."""
    required = {"task_id", "trial_id", "reported_success"}
    require(
        type(record) is dict
        and required <= set(record) <= required | {"baseline", "final", "goal"},
        "invalid trial fields",
    )
    for key in ("task_id", "trial_id"):
        identifier(record[key], key)
    require(type(record["reported_success"]) is bool, "reported_success must be Boolean")
    coverage = {key: key in record for key in ("baseline", "final", "goal")}
    for key in ("baseline", "final"):
        if coverage[key]:
            snapshot = record[key]
            fields(snapshot, {"observed_at", "state"}, key)
            timestamp(snapshot["observed_at"])
            require(type(snapshot["state"]) is dict, "snapshot state must be object")
            json_value(snapshot["state"])
    if coverage["goal"]:
        goal = record["goal"]
        fields(goal, {"state", "mutation_paths"}, "goal")
        require(type(goal["state"]) is dict, "goal state must be object")
        json_value(goal["state"])
        require(type(goal["mutation_paths"]) is list, "mutation_paths must be a list")
        require(len(goal["mutation_paths"]) <= 9999, "too many mutation targets")
        for path in goal["mutation_paths"]:
            require(type(path) is list and 0 < len(path) < 32, "invalid mutation path")
            value = goal["state"]
            for key in path:
                identifier(key, "mutation path key")
                require(type(value) is dict and key in value, "mutation target absent from goal")
                value = value[key]
    result = {key: record[key] for key in sorted(required)} | {"coverage": coverage}
    missing = [key for key, present in coverage.items() if not present]
    if missing:
        return result | {"status": "unobserved", "missing_inputs": missing, "counts": None}
    before, final, goal = record["baseline"], record["final"], record["goal"]
    requirement = {
        "id": "full-state",
        "subject": "database",
        "path": ["database"],
        "expected": goal["state"],
        "observation_id": "final",
        "baseline_id": "baseline",
        "max_age_seconds": 0,
        "action_id": None,
    }
    requirements = [requirement]
    for index, path in enumerate(goal["mutation_paths"]):
        expected = goal["state"]
        for key in path:
            expected = expected[key]
        requirements.append(
            requirement
            | {
                "id": f"mutation-{index}",
                "path": ["database", *path],
                "expected": expected,
                "requires_change": True,
            }
        )
    packet = {
        "schema_version": 2,
        "as_of": final["observed_at"],
        "actions": [],
        "requirements": requirements,
        "observations": [
            {
                "id": "final",
                "subject": "database",
                "observed_at": final["observed_at"],
                "state": {"database": final["state"]},
            }
        ],
        "baselines": [
            {
                "id": "baseline",
                "subject": "database",
                "observed_at": before["observed_at"],
                "state": {"database": before["state"]},
            }
        ],
    }
    report = check_packet(packet)
    status = next(
        (s for s in ("contradicted", "unobserved", "unconfirmed") if report["counts"][s]),
        "confirmed",
    )
    return result | {"status": status, "missing_inputs": [], "counts": report["counts"]}


def summarize(records: list[dict]) -> dict:
    results = [evaluate(record) for record in records]
    ids = [(row["task_id"], row["trial_id"]) for row in results]
    require(len(ids) == len(set(ids)), "duplicate task/trial identity")
    coverage = {
        key: sum(row["coverage"][key] for row in results) for key in ("baseline", "final", "goal")
    }
    coverage["complete"] = sum(all(row["coverage"].values()) for row in results)
    counts = Counter(row["status"] for row in results)
    cross = {
        str(flag).lower(): {
            status: sum(
                row["reported_success"] == flag and row["status"] == status for row in results
            )
            for status in STATUSES
        }
        for flag in (True, False)
    }
    return {
        "projection": "entire supplied database plus explicit mutation paths",
        "trials": len(results),
        "coverage": coverage,
        "counts": {status: counts[status] for status in STATUSES},
        "by_reported_success": cross,
        "results": results,
    }


def missing_archive(raw: bytes) -> dict:
    require(hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, "source checksum mismatch")
    records = json.loads(raw, object_pairs_hook=unique_pairs)
    # This pinned archive has no supplied full snapshots. Never infer them from tools/hashes.
    for row in records:
        require(set(row) == {"task_id", "trial", "reward", "info", "traj"}, "archive shape changed")
        require(
            not (
                {"baseline", "final", "goal", "initial_state", "final_state", "goal_state"}
                & set(row["info"])
            ),
            "unexpected snapshot field; mapping needs review",
        )
    result = summarize(
        [
            {
                "task_id": str(row["task_id"]),
                "trial_id": str(row["trial"]),
                "reported_success": row["reward"] == 1.0,
            }
            for row in records
        ]
    )
    return {
        "source": SOURCE,
        "source_sha256": SOURCE_SHA256,
        "license": "MIT",
        "scope": "missing-input inventory of pinned archive; no full-state outcome verified",
        "prior_projection": {
            "reported_successes": 84,
            "confirmed": 13,
            "contradicted": 9,
            "unobserved": 62,
        },
        **result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pinned-tau-archive", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    if args.pinned_tau_archive:
        result = missing_archive(raw)
    else:
        value = json.loads(raw, object_pairs_hook=unique_pairs)
        fields(value, {"source", "version", "license", "projection", "records"}, "corpus")
        for key in ("source", "version", "license"):
            require(type(value[key]) is str and bool(value[key].strip()), f"missing {key}")
        require(value["projection"] == "entire supplied database", "unsupported projection")
        require(type(value["records"]) is list, "records must be a list")
        result = {
            "source": value["source"],
            "version": value["version"],
            "license": value["license"],
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            **summarize(value["records"]),
        }
    require(args.output.resolve() != args.input.resolve(), "output cannot replace input")
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"PASS: {result['trials']} trials; {result['coverage']['complete']} complete states")


if __name__ == "__main__":
    main()
