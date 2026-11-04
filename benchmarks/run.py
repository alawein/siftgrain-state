"""Pinned public-trajectory fault injection. Not full-task gold or model evaluation."""

import argparse
import hashlib
import json
import platform
import shutil
import time
import tracemalloc
import urllib.request
import zipfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

from siftgrain_state.core import check_packet, same_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data-v1"
SHA = "e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa"
URL = "https://raw.githubusercontent.com/sierra-research/tau-bench/59a200c6d575d595120f1cb70fea53cef0632f6b/historical_trajectories/gpt-4o-airline.json"
STATES = ("confirmed", "contradicted", "unobserved", "unconfirmed")


def cases(records):
    rows, keys = [], {}
    for index, record in enumerate(records):
        snapshots = []
        for message in record.get("traj", []):
            if message.get("role") != "tool":
                continue
            try:
                state = json.loads(message.get("content", ""))
            except (ValueError, TypeError):
                continue
            if type(state) is dict and "reservation_id" in state and "error" not in state:
                snapshots.append(state)
        if not snapshots:
            continue
        state = snapshots[-1]
        packet = {
            "schema_version": 3,
            "as_of": "2026-10-13T12:00:00Z",
            "actions": [{"id": "action", "status": "succeeded"}],
            "observations": [
                {
                    "id": "final",
                    "subject": str(state["reservation_id"]),
                    "observed_at": "2026-10-13T11:59:30Z",
                    "state": {"reservation": state},
                }
            ],
            "baselines": [
                {
                    "id": "before",
                    "subject": str(state["reservation_id"]),
                    "observed_at": "2026-10-13T11:58:00Z",
                    "state": {"reservation": None},
                }
            ],
            "requirements": [
                {
                    "id": "state",
                    "subject": str(state["reservation_id"]),
                    "path": ["reservation"],
                    "expected": state,
                    "observation_id": "final",
                    "baseline_id": "before",
                    "requires_change": True,
                    "max_age_seconds": 60,
                    "action_id": "action",
                }
            ],
        }
        for fault, gold in [
            ("clean", "confirmed"),
            ("noop", "unconfirmed"),
            ("stale", "unobserved"),
            ("subject", "unobserved"),
            ("timezone-skew", "unobserved"),
            ("wrong-state", "contradicted"),
        ]:
            p = deepcopy(packet)
            if fault == "noop":
                p["baselines"][0]["state"] = deepcopy(p["observations"][0]["state"])
            elif fault == "stale":
                p["observations"][0]["observed_at"] = "2026-10-13T11:58:59Z"
            elif fault == "subject":
                p["observations"][0]["subject"] = "wrong-subject"
            elif fault == "timezone-skew":
                p["observations"][0]["observed_at"] = "2026-10-13T11:59:30-07:00"
            elif fault == "wrong-state":
                p["observations"][0]["state"]["reservation"] = None
            identity = f"{index}:{fault}"
            rows.append(
                {
                    "id": identity,
                    "source_index": index,
                    "task_id": record.get("task_id"),
                    "split": "dev"
                    if int(
                        hashlib.sha256(str(record.get("task_id", index)).encode()).hexdigest(), 16
                    )
                    % 5
                    == 0
                    else "test",
                    "fault": fault,
                    "packet": p,
                }
            )
            keys[identity] = gold
    return rows, keys


def verify_predictions(predictions, keys):
    if set(predictions) != set(keys) or predictions != keys:
        raise AssertionError("verdict regression or gold denominator mismatch")


def metrics(predictions, keys):
    scores = {}
    for state in STATES:
        tp = sum(predictions[k] == state and gold == state for k, gold in keys.items())
        predicted = sum(v == state for v in predictions.values())
        actual = sum(v == state for v in keys.values())
        scores[state] = {
            "tp": tp,
            "predicted": predicted,
            "actual": actual,
            "precision": tp / predicted if predicted else None,
            "recall": tp / actual if actual else None,
        }
    return {
        "accuracy": sum(predictions[k] == gold for k, gold in keys.items()) / len(keys),
        "states": scores,
    }


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch", action="store_true", help="fetch pinned public data (outside offline core)"
    )
    parser.add_argument(
        "--source", type=Path, default=ROOT.parent / "studies/data/gpt-4o-airline.json"
    )
    args = parser.parse_args()
    if args.fetch:
        args.source.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            raw = response.read(6 * 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != SHA:
            raise ValueError("download checksum mismatch")
        args.source.write_bytes(raw)
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError("source checksum mismatch")
    records = json.loads(raw)
    rows, keys = cases(records)
    DATA.mkdir(exist_ok=True)
    # Public data derivatives are local build artifacts; no transcript redistribution in Git.
    generated = ROOT.parent / "build/benchmark-v1"
    generated.mkdir(parents=True, exist_ok=True)
    for split in ("dev", "test"):
        chosen = [r for r in rows if r["split"] == split]
        write(generated / f"{split}.json", chosen)
        write(generated / f"{split}-answers.json", {r["id"]: keys[r["id"]] for r in chosen})
    from jsonschema import Draft202012Validator

    schema = json.loads((DATA / "cases.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(rows)
    answers_schema = json.loads((DATA / "answers.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(answers_schema)
    for split in ("dev", "test"):
        Draft202012Validator(answers_schema).validate(
            json.loads((generated / f"{split}-answers.json").read_text(encoding="utf-8"))
        )
    packet_schema = json.loads(
        (ROOT.parent / "schemas/v3/packet.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(packet_schema)
    for row in rows:
        validator.validate(row["packet"])
    tracemalloc.start()
    start = time.perf_counter()
    predictions = {r["id"]: check_packet(r["packet"])["results"][0]["status"] for r in rows}
    seconds = time.perf_counter() - start
    verify_predictions(predictions, keys)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    repeated = {r["id"]: check_packet(r["packet"])["results"][0]["status"] for r in reversed(rows)}
    if predictions != repeated:
        raise AssertionError("order nondeterminism")
    naive = {
        r["id"]: (
            "confirmed"
            if same_json(
                r["packet"]["requirements"][0]["expected"],
                r["packet"]["observations"][0]["state"]["reservation"],
            )
            else "contradicted"
        )
        for r in rows
    }
    result = {
        "source_sha256": SHA,
        "public_trajectories": len(records),
        "eligible_trajectories": len(rows) // 6,
        "cases": len(rows),
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "checker": metrics(predictions, keys),
        "naive_equality": metrics(naive, keys),
        "fault_accuracy": {
            f: sum(predictions[r["id"]] == keys[r["id"]] for r in rows if r["fault"] == f)
            / sum(r["fault"] == f for r in rows)
            for f in sorted({r["fault"] for r in rows})
        },
        "seconds": seconds,
        "cases_per_second": len(rows) / seconds,
        "peak_python_bytes": peak,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "order_deterministic": True,
        "native_baseline": (
            "Not executed: archive omits full databases/goals; native checker replays tools."
        ),
        "llm_baseline": "Omitted: no model calls; controlled fault labels.",
        "confidence_intervals": "Not reported: correlated faults, not a population sample.",
    }
    write(ROOT / "results.json", result)
    metadata = json.loads((DATA / "croissant.json").read_text(encoding="utf-8"))
    for file in metadata["distribution"]:
        file["sha256"] = hashlib.sha256((generated / file["name"]).read_bytes()).hexdigest()
    write(DATA / "croissant.json", metadata)
    for path in DATA.iterdir():
        if path.is_file():
            shutil.copyfile(path, generated / path.name)
    checksums = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(generated.iterdir())
        if p.name != "checksums.json"
    }
    write(generated / "checksums.json", checksums)
    with zipfile.ZipFile(
        ROOT.parent / "build/siftgrain-state-data-v1.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for p in sorted(generated.iterdir()):
            archive.write(p, p.name)
    print(
        json.dumps(
            {"cases": len(rows), "accuracy": result["checker"]["accuracy"], "seconds": seconds}
        )
    )


if __name__ == "__main__":
    main()
