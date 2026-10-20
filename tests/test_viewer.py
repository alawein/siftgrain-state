import base64
import hashlib
import html
import json
import re
import runpy
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_outcomes import packet as make_packet

from outcome_check.cli import main
from outcome_check.contract import InputError, validate
from outcome_check.core import check_packet
from outcome_check.report import render_html, render_json


def _download_hrefs(page):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.downloads = {}

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "a" and values.get("download"):
                self.downloads[values["download"]] = values["href"]

    parser = Links()
    parser.feed(page)
    return parser.downloads


def test_help_mentions_example_exit_codes_and_docs(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "examples/packet.json" in out
    assert "exit" in out.lower()
    assert "contract" in out.lower()


def test_contract_errors_include_row_index():
    bad = make_packet()
    bad["requirements"][0]["max_age_seconds"] = -1
    with pytest.raises(InputError) as excinfo:
        validate(bad)
    assert "row 1" in str(excinfo.value)

    dup = make_packet()
    dup["observations"].append(dict(dup["observations"][0]))
    with pytest.raises(InputError) as excinfo:
        validate(dup)
    assert "row 2" in str(excinfo.value)

    bad_time = make_packet()
    bad_time["observations"][0]["observed_at"] = "not-a-time"
    with pytest.raises(InputError) as excinfo:
        validate(bad_time)
    assert "row 1" in str(excinfo.value)


def test_fractional_age_renders_as_decimal():
    p = make_packet()
    p["as_of"] = "2026-10-04T12:00:00.5Z"
    report = check_packet(p)
    page = render_html(report, p)
    assert "121/2" not in page
    assert "age 60.5 s" in page


def test_html_without_packet_uses_placeholder_cells():
    report = check_packet(make_packet())
    page = render_html(report)
    assert "—" in page
    assert "missing observation" not in page


def test_html_missing_observation_and_bad_as_of_fallback():
    p = make_packet()
    p["requirements"][0]["observation_id"] = "absent"
    report = check_packet(p)
    assert "missing observation" in render_html(report, p)
    broken = make_packet()
    broken.pop("as_of")
    page = render_html(check_packet(make_packet()), broken)
    assert "max " in page


def test_html_empty_results_has_no_table():
    page = render_html({"counts": {}, "results": [], "exit_code": 0})
    assert "<table" not in page


def test_age_equal_to_max_is_confirmed():
    p = make_packet()
    # observed 60 s before as_of; max exactly 60 keeps it fresh.
    p["requirements"][0]["max_age_seconds"] = 60
    result = check_packet(p)
    assert result["results"][0]["outcome"] == "confirmed"
    assert result["results"][0]["status"] == "confirmed"


def test_fractional_as_of_age():
    p = make_packet()
    p["as_of"] = "2026-10-04T12:00:00.5Z"
    p["requirements"][0]["max_age_seconds"] = 61
    result = check_packet(p)
    assert result["results"][0]["outcome"] == "confirmed"
    p["requirements"][0]["max_age_seconds"] = 60
    result = check_packet(p)
    assert result["results"][0]["reason"] == "stale observation"


def test_cli_missing_input_returns_two(capsys, tmp_path):
    missing = tmp_path / "does-not-exist.json"
    assert main([str(missing)]) == 2
    assert "outcome-check" in capsys.readouterr().err


def test_cli_missing_output_dir_returns_two(tmp_path):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(make_packet()), encoding="utf-8")
    target = tmp_path / "no-such-dir" / "out.json"
    assert main([str(source), "--json", str(target)]) == 2
    assert not target.exists()


def test_html_viewer_has_table_how_to_read_and_evidence():
    p = make_packet()
    report = check_packet(p)
    page = render_html(report, p)
    assert "<table" in page
    assert "How to read" in page
    assert "action receipt" in page.lower()
    assert "confirmed" in page.lower()
    # Evidence echo: expected path/value and observed value plus age vs max.
    assert "time" in page
    assert "07:00" in page
    assert "max" in page.lower()
    assert "<script>" not in page


def test_html_escapes_malicious_evidence():
    p = make_packet()
    p["requirements"][0]["id"] = "<script>alert(1)</script>"
    p["requirements"][0]["expected"] = "<b>bold</b>"
    report = check_packet(p)
    page = render_html(report, p)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "&lt;b&gt;" in page


@pytest.mark.parametrize(
    "text,display",
    [
        ("high \ud800", r"high \ud800"),
        ("low \udfff", r"low \udfff"),
        ("separate \ud800 \udfff", r"separate \ud800 \udfff"),
        ("Málaga 水 😀 �", "Málaga 水 😀 �"),
    ],
)
def test_html_exports_unsigned_surrogates_as_visible_escapes(text, display):
    p = make_packet()
    # Cover evidence cells and identifiers repeated in the enhanced timeline.
    value = text + " <script>alert(1)</script>"
    p["requirements"][0].update(id=value, expected=value, observation_id=value, action_id=value)
    p["actions"][0]["id"] = value
    p["observations"][0].update(id=value, state={"time": value})
    report = check_packet(p)
    report_bytes = render_json(report).encode("utf-8")
    page = render_html(
        report,
        p,
        download_links={"Report": "report.json"},
        download_files={"report.json": report_bytes},
    )
    assert page.encode("utf-8").decode("utf-8") == page
    shown = html.escape(display + " <script>alert(1)</script>")
    table = page.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    timeline = page.split('<ol class="timeline">', 1)[1].split("</ol>", 1)[0]
    assert shown in table
    assert shown in timeline
    assert "<script>alert(1)</script>" not in page
    assert report["results"][0]["status"] == "confirmed"
    embedded = _download_hrefs(page)["report.json"].split(",", 1)[1]
    assert base64.b64decode(embedded, validate=True) == report_bytes
    assert json.loads(report_bytes) == report


@pytest.mark.parametrize(
    "text,display",
    [
        ("high \ud800", r"high \ud800"),
        ("low \udfff", r"low \udfff"),
        ("Málaga 水 😀 �", "Málaga 水 😀 �"),
    ],
)
def test_cli_html_export_preserves_unsigned_json_report(tmp_path, capsys, text, display):
    p = make_packet()
    p["requirements"][0]["expected"] = text
    p["observations"][0]["state"]["time"] = text
    packet_bytes = json.dumps(p).encode("utf-8")
    source = tmp_path / "packet.json"
    source.write_bytes(packet_bytes)
    html_output = tmp_path / "report.html"
    json_output = tmp_path / "report.json"
    expected = check_packet(p)
    expected["input_sha256"] = hashlib.sha256(packet_bytes).hexdigest()

    assert main([str(source), "--json", str(json_output), "--html", str(html_output)]) == 0
    assert capsys.readouterr().err == ""
    page = html_output.read_text(encoding="utf-8")
    assert display in page
    assert json_output.read_bytes() == render_json(expected).encode("utf-8")
    assert source.read_bytes() == packet_bytes


def test_html_truncates_large_state_with_marker():
    p = make_packet()
    big = "X" * 5000
    p["observations"][0]["state"] = {"time": big}
    p["requirements"][0]["expected"] = big
    report = check_packet(p)
    page = render_html(report, p)
    assert "truncat" in page.lower()
    assert big not in page


def test_generic_html_does_not_claim_executed_demo():
    p = make_packet()
    page = render_html(check_packet(p), p)
    assert "static executed example" not in page.lower()
    assert "synthetic refund" not in page.lower()
    assert "not supplied" in page


def test_baseline_is_only_the_explicit_matching_observation():
    p = make_packet()
    p["observations"].append(
        {
            "id": "before",
            "subject": "alarm",
            "observed_at": "2026-10-04T11:58:00Z",
            "state": {"time": "06:00"},
        }
    )
    report = check_packet(p)
    page = render_html(report, p, baseline_observation_id="before")
    evidence = page.split("<h2>Inspectable report</h2>")[0]
    assert "06:00" in evidence
    assert "observation before" in evidence
    assert "2026-10-04T11:58:00Z" in evidence
    assert "07:00" in evidence
    assert 'data-label="Before / baseline"' in evidence
    generic = render_html(report, p).split("<h2>Inspectable report</h2>")[0]
    assert "06:00" not in generic
    assert "not supplied" in generic
    missing = render_html(report, p, baseline_observation_id="absent")
    assert "missing baseline observation" in missing
    p["observations"][-1]["subject"] = "other"
    wrong_subject = render_html(report, p, baseline_observation_id="before")
    assert "baseline subject mismatch" in wrong_subject
    assert "06:00" not in wrong_subject


@pytest.mark.parametrize(
    "observed_at,label,age",
    [
        ("2026-10-04T11:59:00Z", "fresh", "60"),
        ("2026-10-04T11:45:00Z", "stale", "900"),
        ("2026-10-04T12:00:01Z", "future", "-1"),
    ],
)
def test_freshness_exposes_eligibility_and_supplied_comparison_time(observed_at, label, age):
    p = make_packet()
    p["observations"][0]["observed_at"] = observed_at
    page = render_html(check_packet(p), p).split("<h2>Inspectable report</h2>")[0]
    assert f"{label}; age {age} s / max 120 s" in page
    assert "2026-10-04T12:00:00Z" in page
    assert observed_at in page


def test_wrong_subject_echo_cannot_look_like_accepted_evidence():
    p = make_packet()
    p["observations"][0]["subject"] = "other-device"
    page = render_html(check_packet(p), p).split("<h2>Inspectable report</h2>")[0]
    assert "subject other-device" in page
    assert "subject mismatch" in page


def test_freshness_keeps_submicrosecond_precision_in_evidence_echo():
    p = make_packet()
    p["as_of"] = "2026-10-04T12:00:00.0000001Z"
    page = render_html(check_packet(p), p).split("<h2>Inspectable report</h2>")[0]
    assert "age 60.0000001 s / max 120 s" in page


def test_demo_context_is_explicit_escaped_and_downloads_are_local_files():
    p = make_packet()
    report = check_packet(p)
    page = render_html(
        report,
        p,
        demo_title="Synthetic refund <script>alert(1)</script>",
        demo_note="Synthetic, AI-assisted, non-client <b>example</b>",
        download_links={
            "Packet <img>": "acceptance.json",
            "Report": "acceptance-report.json",
            "Unsafe": "javascript:alert(1)",
            "Remote": "https://example.com/packet.json",
            "Traversal": "../packet.json",
        },
    )
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "&lt;b&gt;example&lt;/b&gt;" in page
    assert (
        "<title>Synthetic refund &lt;script&gt;alert(1)&lt;/script&gt; | outcome report</title>"
    ) in page
    assert 'href="acceptance.json" download' in page
    assert 'href="acceptance-report.json" download' in page
    assert "Packet &lt;img&gt;" in page
    assert "javascript:" not in page
    assert "https://example.com" not in page
    assert "../packet.json" not in page


@pytest.mark.parametrize(
    "filename,payload,mime",
    [
        (
            "proof.json",
            b'{"text":"<script>alert(1)</script>"}\r\n',
            "application/json",
        ),
        ("proof.txt", b"Refund caf\xc3\xa9\r\n", "text/plain;charset=utf-8"),
        ("empty.bin", b"", "application/octet-stream"),
    ],
)
def test_embedded_download_keeps_exact_bytes_and_rejects_unsafe_names(filename, payload, mime):
    p = make_packet()
    page = render_html(
        check_packet(p),
        p,
        download_links={
            "Evidence <script>": filename,
            "Fallback": "fallback.txt",
            "Traversal": "../outside.json",
            "Unsafe": "javascript:alert(1)",
        },
        download_files={
            filename: payload,
            "unlinked.json": b"unused",
            "../outside.json": b"outside",
            "javascript:alert(1)": b"unsafe",
        },
    )
    links = _download_hrefs(page)
    assert set(links) == {filename, "fallback.txt"}
    prefix, encoded = links[filename].split(",", 1)
    assert prefix == f"data:{mime};base64"
    assert base64.b64decode(encoded, validate=True) == payload
    assert links["fallback.txt"] == "fallback.txt"
    assert "Evidence &lt;script&gt;" in page
    assert "<script>" not in page
    assert "../outside.json" not in page
    assert "javascript:" not in page


def test_build_demo_keeps_alarm_snapshot_and_exports_acceptance(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    examples = tmp_path / "examples"
    examples.mkdir()
    for filename in ("packet.json", "acceptance.json", "acceptance-source.txt"):
        (examples / filename).write_bytes((root / "examples" / filename).read_bytes())
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(root / "scripts" / "build_demo.py"), run_name="__main__")
    site = tmp_path / "site"
    alarm_snapshot = json.loads((root / "examples" / "report.json").read_text(encoding="utf-8"))
    assert json.loads((site / "report.json").read_text(encoding="utf-8")) == alarm_snapshot | {
        "provenance": "Synthetic, AI-assisted, non-client"
    }
    packet_bytes = (examples / "acceptance.json").read_bytes()
    assert (site / "acceptance.json").read_bytes() == packet_bytes
    assert (site / "acceptance-source.txt").read_bytes() == (
        examples / "acceptance-source.txt"
    ).read_bytes()
    report = json.loads((site / "acceptance-report.json").read_text(encoding="utf-8"))
    assert report["input_sha256"] == hashlib.sha256(packet_bytes).hexdigest()
    assert report["counts"] == {"confirmed": 1, "contradicted": 1, "unobserved": 2}
    assert report["provenance"] == "Synthetic, AI-assisted, non-client; original CC0 example"
    assert set(report) == {
        "schema_version",
        "results",
        "counts",
        "exit_code",
        "input_sha256",
        "provenance",
    }
    page = (site / "acceptance.html").read_text(encoding="utf-8")
    evidence = page.split("<h2>Inspectable report</h2>")[0]
    assert "Synthetic refund acceptance" in evidence
    assert "Agent Acceptance" in evidence
    assert hashlib.sha256((examples / "acceptance-source.txt").read_bytes()).hexdigest() in evidence
    assert "refund-baseline" in evidence
    assert "already true" in evidence
    assert "3 confirmed" in evidence
    assert "1 unobserved" in evidence
    links = _download_hrefs(evidence)
    assert set(links) == {"acceptance.json", "acceptance-report.json", "acceptance-source.txt"}
    for filename, href in links.items():
        prefix, encoded = href.split(",", 1)
        assert prefix.startswith("data:") and prefix.endswith(";base64")
        assert base64.b64decode(encoded, validate=True) == (site / filename).read_bytes()


def test_pages_build_exports_all_demos_with_exact_evidence(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    examples = tmp_path / "examples"
    examples.mkdir()
    for filename in (
        "packet.json",
        "acceptance.json",
        "acceptance-source.txt",
        "state.packet.json",
    ):
        (examples / filename).write_bytes((root / "examples" / filename).read_bytes())
    workflow = (root / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    builders = re.findall(
        r"^\s+- run: uv run python (scripts/build_[a-z_]+\.py)\s*$", workflow, re.MULTILINE
    )
    monkeypatch.chdir(tmp_path)
    for builder in builders:
        runpy.run_path(str(root / builder), run_name="__main__")
    site = tmp_path / "site"
    required = {
        "index.html",
        "report.json",
        "acceptance.html",
        "acceptance.json",
        "acceptance-report.json",
        "acceptance-source.txt",
        "state.html",
        "state.packet.json",
        "state.report.json",
    }
    assert required <= {path.name for path in site.iterdir() if path.stat().st_size}
    packet_bytes = (examples / "state.packet.json").read_bytes()
    assert (site / "state.packet.json").read_bytes() == packet_bytes
    report = json.loads((site / "state.report.json").read_text(encoding="utf-8"))
    assert report["input_sha256"] == hashlib.sha256(packet_bytes).hexdigest()
    assert report["counts"] == {
        "confirmed": 1,
        "contradicted": 1,
        "unobserved": 1,
        "unconfirmed": 1,
    }
    assert report["exit_code"] == 1
    page = (site / "state.html").read_text(encoding="utf-8")
    assert "Siftgrain State: four evidence states" in page
    assert "Synthetic, AI-assisted, non-client" in page
    links = _download_hrefs(page)
    assert set(links) == {"state.packet.json", "state.report.json"}
    for filename, href in links.items():
        prefix, encoded = href.split(",", 1)
        assert prefix.startswith("data:") and prefix.endswith(";base64")
        assert base64.b64decode(encoded, validate=True) == (site / filename).read_bytes()
    assert (site / "acceptance.json").read_bytes() == (examples / "acceptance.json").read_bytes()
    assert (site / "acceptance-source.txt").read_bytes() == (
        examples / "acceptance-source.txt"
    ).read_bytes()


def test_v2_html_shows_signature_and_required_baseline_change():
    from test_checks_v2 import baseline_packet

    p = baseline_packet()
    page = render_html(check_packet(p), p)
    assert '<th scope="col">Signature</th>' in page
    assert '<td data-label="Signature">unsigned</td>' in page
    assert "unconfirmed" in page
    assert "baseline before" in page
    assert "change required" in page


def test_v2_card_shows_its_required_baseline_value():
    from test_checks_v2 import baseline_packet

    p = baseline_packet()
    page = render_html(check_packet(p), p).split("<h2>Inspectable report</h2>")[0]
    assert "observation before; observed at" in page
