import argparse
import sys
from pathlib import Path

from siftgrain_state.contract import InputError, load_packet
from siftgrain_state.core import check_packet
from siftgrain_state.output import atomic_write, validate_outputs
from siftgrain_state.report import render_html, render_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check supplied agent outcome receipts.",
        epilog=(
            "packet shape: schema_version 1 with as_of, requirements, actions, "
            "observations; see docs/contract.md. "
            "example: outcome-check examples/packet.json --html report.html. "
            "exit 0 all confirmed; exit 1 needs review; exit 2 invalid input or I/O."
        ),
    )
    parser.add_argument("packet", type=Path, help="input packet JSON file")
    parser.add_argument(
        "--public-keys", type=Path, help="local Ed25519 public keys JSON; requires signing extra"
    )
    parser.add_argument("--json", type=Path, help="write the JSON report to PATH")
    parser.add_argument("--html", type=Path, help="write the HTML report to PATH")
    parser.add_argument("--force", action="store_true", help="overwrite existing output files")
    args = parser.parse_args(argv)
    try:
        packet, digest = load_packet(args.packet)
        verifier = None
        if args.public_keys is not None:
            from siftgrain_state.signatures import load_public_keys

            verifier = load_public_keys(args.public_keys)
        report = check_packet(packet, verifier) | {"input_sha256": digest}
        targets = [(args.json, render_json(report)), (args.html, render_html(report, packet))]
        outputs = [path for path, content in targets if path is not None]
        inputs = [args.packet] + ([args.public_keys] if args.public_keys is not None else [])
        validate_outputs(outputs, inputs, args.force)
        for path, content in targets:
            if path is not None:
                atomic_write(path, content, args.force)
        if args.json is None:
            sys.stdout.write(render_json(report))
        return report["exit_code"]
    except (InputError, OSError, ValueError, OverflowError, RecursionError, ImportError) as exc:
        print(f"outcome-check: {exc}", file=sys.stderr)
        return 2
