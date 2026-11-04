"""CLI for explicit local harness projections; same atomic output policy as checker."""

import argparse
import json
import sys
from pathlib import Path

from siftgrain_state.adapters import convert
from siftgrain_state.contract import InputError, invalid_constant, require, unique_pairs
from siftgrain_state.output import atomic_write, validate_outputs
from siftgrain_state.report import render_json


def read_json(path: Path):
    with path.open("rb") as stream:
        raw = stream.read(5 * 1024 * 1024 + 1)
    require(len(raw) <= 5 * 1024 * 1024, "input exceeds 5 MiB")
    require(not raw.startswith(b"\xef\xbb\xbf"), "BOM forbidden")
    return json.loads(
        raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=invalid_constant
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", choices=("tau", "swebench", "inspect"))
    parser.add_argument("source", type=Path)
    parser.add_argument("--goal", type=Path, help="explicit goal object for tau/Inspect")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--max-age-seconds", type=int, required=True)
    parser.add_argument("--baseline-at")
    parser.add_argument("--requires-change", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        packet = convert(
            args.adapter,
            read_json(args.source),
            as_of=args.as_of,
            observed_at=args.observed_at,
            max_age_seconds=args.max_age_seconds,
            expected=read_json(args.goal) if args.goal else None,
            baseline_at=args.baseline_at,
            requires_change=args.requires_change,
        )
        if args.output:
            validate_outputs(
                [args.output], [args.source] + ([args.goal] if args.goal else []), args.force
            )
            atomic_write(args.output, render_json(packet), args.force)
        else:
            sys.stdout.write(render_json(packet))
        return 0
    except (InputError, OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        print(f"outcome-convert: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
