import hashlib
from pathlib import Path

from siftgrain_state.contract import load_packet
from siftgrain_state.core import check_packet
from siftgrain_state.report import render_html, render_json


def main() -> None:
    packet, digest = load_packet(Path("examples/packet.json"))
    report = check_packet(packet) | {
        "input_sha256": digest,
        "provenance": "Synthetic, AI-assisted, non-client",
    }
    target = Path("site")
    target.mkdir(exist_ok=True)
    (target / "index.html").write_text(render_html(report, packet), encoding="utf-8")
    (target / "report.json").write_text(render_json(report), encoding="utf-8")

    acceptance_path = Path("examples/acceptance.json")
    acceptance, acceptance_digest = load_packet(acceptance_path)
    source_bytes = Path("examples/acceptance-source.txt").read_bytes()
    acceptance_bytes = acceptance_path.read_bytes()
    if hashlib.sha256(acceptance_bytes).hexdigest() != acceptance_digest:
        raise ValueError("acceptance packet changed while building the demo")
    acceptance_report = check_packet(acceptance) | {
        "input_sha256": acceptance_digest,
        "provenance": "Synthetic, AI-assisted, non-client; original CC0 example",
    }
    acceptance_report_bytes = render_json(acceptance_report).encode("utf-8")
    acceptance_page = render_html(
        acceptance_report,
        acceptance,
        baseline_observation_id="refund-baseline",
        demo_title="Agent Acceptance: Synthetic refund acceptance",
        demo_note=(
            "Static executed example. Synthetic, AI-assisted, non-client; original CC0 data. "
            f"Source text SHA-256: {hashlib.sha256(source_bytes).hexdigest()}. "
            + source_bytes.decode("utf-8").strip()
        ),
        download_links={
            "Download exact packet": "acceptance.json",
            "Download report + input hash": "acceptance-report.json",
            "Download source narrative": "acceptance-source.txt",
        },
        download_files={
            "acceptance.json": acceptance_bytes,
            "acceptance-report.json": acceptance_report_bytes,
            "acceptance-source.txt": source_bytes,
        },
    )
    (target / "acceptance.html").write_text(acceptance_page, encoding="utf-8")
    (target / "acceptance-report.json").write_bytes(acceptance_report_bytes)
    (target / "acceptance.json").write_bytes(acceptance_bytes)
    (target / "acceptance-source.txt").write_bytes(source_bytes)


if __name__ == "__main__":
    main()
