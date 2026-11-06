"""Build the four-state synthetic showcase without altering legacy demo outputs."""

from pathlib import Path

from siftgrain_state.contract import load_packet
from siftgrain_state.core import check_packet
from siftgrain_state.report import render_html, render_json


def main():
    path = Path("examples/state.packet.json")
    packet, digest = load_packet(path)
    report = check_packet(packet) | {
        "input_sha256": digest,
        "provenance": "Synthetic, non-client; CC0",
    }
    target = Path("site")
    target.mkdir(exist_ok=True)
    page = render_html(
        report,
        packet,
        synthetic=True,
        demo_title="Siftgrain State: four evidence states",
        demo_note="Synthetic, non-client. Baseline protects against a no-op claim.",
        download_links={"Packet": "state.packet.json", "JSON report": "state.report.json"},
        download_files={
            "state.packet.json": path.read_bytes(),
            "state.report.json": render_json(report).encode(),
        },
    )
    (target / "state.html").write_text(page, encoding="utf-8", newline="\n")
    (target / "state.packet.json").write_bytes(path.read_bytes())
    (target / "state.report.json").write_text(render_json(report), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
