import base64
import html
import json
import re
from fractions import Fraction

from outcome_check.contract import InputError, age_seconds


def render_json(report: dict) -> str:
    return json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _truncate_text(value: str, limit: int = 400) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"… [truncated {len(value) - limit} chars]"


def _short_json(value: object, limit: int = 400) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raw = str(value)
    return _truncate_text(raw, limit)


def _walk(state: object, path: list) -> tuple[bool, object]:
    value = state
    for key in path:
        if type(value) is not dict or key not in value:
            return False, None
        value = value[key]
    return True, value


def _index(rows: object, key: str = "id") -> dict:
    if not isinstance(rows, list):
        return {}
    return {row.get(key): row for row in rows if isinstance(row, dict) and key in row}


def _decimal_age(value: Fraction) -> str:
    """Keep every supplied fractional digit in the finite decimal timestamp age."""
    whole, remainder = divmod(abs(value.numerator), value.denominator)
    digits = ""
    while remainder:
        digit, remainder = divmod(remainder * 10, value.denominator)
        digits += str(digit)
    return ("-" if value < 0 else "") + str(whole) + ("." + digits if digits else "")


def _baseline_cell(req: dict, observations: dict, baseline_id: str | None) -> str:
    if baseline_id is None:
        return "not supplied"
    baseline = observations.get(baseline_id)
    if baseline is None:
        return f"missing baseline observation {baseline_id}"
    if baseline.get("subject") != req.get("subject"):
        return f"baseline subject mismatch (observation {baseline_id})"
    found, value = _walk(baseline.get("state"), req.get("path", []))
    shown = _short_json(value) if found else "missing object path"
    return f"{shown} (observation {baseline_id}; observed at {baseline.get('observed_at')})"


def _evidence_cells(
    result: dict,
    requirements: dict,
    observations: dict,
    as_of: object,
    baseline_id: str | None,
    baselines: dict,
) -> tuple[str, str, str, str]:
    """Return expected, observed, explicit baseline and freshness text, unescaped."""
    req = requirements.get(result.get("id"))
    if req is None:
        return "\u2014", "\u2014", "not supplied", "\u2014"
    path = req.get("path") if isinstance(req.get("path"), list) else []
    dotted = ".".join(str(k) for k in path)
    expected = _short_json(req.get("expected"))
    if req.get("check", "equal") != "equal":
        expected = f"{req['check']} {expected}"
    expected_cell = _truncate_text(f"{dotted} = {expected}") if dotted else expected
    baseline = _baseline_cell(
        req,
        observations if baseline_id is not None else baselines,
        baseline_id if baseline_id is not None else req.get("baseline_id"),
    )
    if req.get("baseline_id") is not None:
        expected_cell += f"; baseline {req['baseline_id']}"
    if req.get("requires_change"):
        expected_cell += "; change required"
    obs = observations.get(req.get("observation_id"))
    if obs is None:
        return expected_cell, "missing observation", baseline, "no observation supplied"
    state = obs.get("state")
    found, value = _walk(state, path)
    observed = _short_json(value) if found else "missing object path"
    observed_cell = f"{observed} (observation {obs.get('id')}; subject {obs.get('subject')})"
    max_age = req.get("max_age_seconds")
    try:
        age = age_seconds(str(as_of), str(obs.get("observed_at")))
        shown = _decimal_age(age)
        eligibility = "future" if age < 0 else "stale" if age > max_age else "fresh"
        freshness = (
            f"{eligibility}; age {shown} s / max {max_age} s (observed at {obs.get('observed_at')})"
        )
    except (InputError, ValueError, TypeError):
        freshness = f"max {max_age} s (observed at {obs.get('observed_at')})"
    return expected_cell, observed_cell, baseline, freshness


def render_html(
    report: dict,
    packet: dict | None = None,
    *,
    baseline_observation_id: str | None = None,
    demo_title: str | None = None,
    demo_note: str | None = None,
    download_links: dict[str, str] | None = None,
    download_files: dict[str, bytes] | None = None,
) -> str:
    content = html.escape(render_json(report))
    cards = "".join(
        f'<div class="card"><strong>{html.escape(str(v))}</strong>'
        f"<span>{html.escape(k.replace('_', ' '))}</span></div>"
        for k, v in report.get("counts", {}).items()
    )
    results = report.get("results")
    if not isinstance(results, list):
        results = []
    packet_map = packet if isinstance(packet, dict) else {}
    requirements = _index(packet_map.get("requirements"))
    observations = _index(packet_map.get("observations"))
    baselines = _index(packet_map.get("baselines"))
    as_of = packet_map.get("as_of")
    title = html.escape(demo_title or "Siftgrain State")
    note = (
        "<details><summary>Demo context and source text hash</summary>"
        f'<p class="demo-note">{html.escape(demo_note)}</p></details>'
        if demo_note
        else ""
    )
    downloads = ""
    for label, filename in (download_links or {}).items():
        if not isinstance(filename, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", filename
        ):
            continue
        href = filename
        payload = (download_files or {}).get(filename)
        if isinstance(payload, bytes):
            mime = {
                "json": "application/json",
                "txt": "text/plain;charset=utf-8",
            }.get(filename.rsplit(".", 1)[-1].lower(), "application/octet-stream")
            href = f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"
        downloads += (
            f'<a href="{html.escape(href, quote=True)}" '
            f'download="{html.escape(filename, quote=True)}">{html.escape(label)}</a>'
        )
    if downloads:
        downloads = f'<nav class="downloads" aria-label="Evidence downloads">{downloads}</nav>'
    comparison = (
        '<p class="comparison"><strong>Supplied comparison time:</strong> '
        f"{html.escape(str(as_of or 'not supplied'))}</p>"
    )
    metadata = (
        '<dl class="metadata"><div><dt>Input SHA-256</dt>'
        f"<dd>{html.escape(str(report.get('input_sha256', 'not supplied')))}</dd></div>"
    )
    if "provenance" in report:
        metadata += (
            f"<div><dt>Provenance</dt><dd>{html.escape(str(report['provenance']))}</dd></div>"
        )
    metadata += "</dl>"
    action_counts = {
        value: sum(isinstance(row, dict) and row.get("action") == value for row in results)
        for value in ("confirmed", "contradicted", "unobserved", "not_required")
    }
    action_summary = (
        '<p class="action-summary">Action receipts alone: '
        + ", ".join(f"{count} {value.replace('_', ' ')}" for value, count in action_counts.items())
        + ". These counts cover requirement rows; "
        "the final status also requires outcome evidence.</p>"
        if results
        else ""
    )
    if results:
        signed = report.get("schema_version") in (2, 3)
        signature_header = '<th scope="col">Signature</th>' if signed else ""
        head = (
            "<thead><tr>"
            '<th scope="col">Requirement</th>'
            '<th scope="col">Status</th>'
            '<th scope="col">Expected</th>'
            '<th scope="col">Observed</th>'
            '<th scope="col">Before / baseline</th>'
            '<th scope="col">Freshness</th>'
            '<th scope="col">Action receipt</th>'
            '<th scope="col">Outcome</th>' + signature_header + '<th scope="col">Reason</th>'
            "</tr></thead>"
        )
        rows = ""
        for item in results:
            if not isinstance(item, dict):
                continue
            expected, observed, baseline, freshness = _evidence_cells(
                item, requirements, observations, as_of, baseline_observation_id, baselines
            )
            status_value = str(item.get("status", ""))
            chip = (
                status_value
                if status_value in ("confirmed", "contradicted", "unobserved", "unconfirmed")
                else ""
            )
            signature_cell = (
                '<td data-label="Signature">'
                f"{html.escape(str(item.get('signature', 'unsigned')))}</td>"
                if signed
                else ""
            )
            rows += (
                "<tr>"
                '<td class="identity" data-label="Requirement">'
                f"{html.escape(str(item.get('id', '')))}</td>"
                f'<td class="st st-{chip}" data-label="Final status">'
                f"{html.escape(status_value)}</td>"
                f'<td data-label="Expected">{html.escape(expected)}</td>'
                f'<td data-label="Observed">{html.escape(observed)}</td>'
                f'<td data-label="Before / baseline">{html.escape(baseline)}</td>'
                f'<td data-label="Freshness">{html.escape(freshness)}</td>'
                '<td data-label="Action receipt">'
                f"{html.escape(str(item.get('action', '')))} "
                f"(action {html.escape(str(item.get('action_id') or 'not required'))})</td>"
                '<td data-label="Outcome">'
                f"{html.escape(str(item.get('outcome', '')))}</td>"
                + signature_cell
                + '<td class="reason" data-label="Engine reason">'
                f"{html.escape(str(item.get('reason', '')))}</td>"
                "</tr>"
            )
        table = (
            "<h2>Results by requirement</h2>"
            "<table><caption>Expected and supplied evidence, followed by the action "
            "receipt and engine verdict.</caption>"
            f"{head}<tbody>{rows}</tbody></table>"
        )
    else:
        table = ""
    how_to = (
        '<details class="reading-guide"><summary>How to read this report</summary>'
        "<ul>"
        "<li>Action receipt keeps what the agent reported: confirmed means the named "
        "action succeeded, contradicted means it failed, unobserved means it is unknown "
        "or missing, and not_required means no action was needed.</li>"
        "<li>Outcome keeps what the supplied observation shows: confirmed means the "
        "requested check was satisfied by fresh evidence, unconfirmed means a required "
        "change was not observed, contradicted means a different value was "
        "observed, and unobserved means the evidence is missing, stale, future, "
        "wrong-subject, or off-path.</li>"
        "<li>Status merges the two: contradicted if either side contradicts, confirmed "
        "only when the outcome confirms and the action confirms or is not required, "
        "otherwise unobserved.</li>"
        "<li>Expected echoes the requirement path and value; Observed echoes the value "
        "at that path in the named observation, even when the engine rejects its "
        "freshness or subject. The engine reason explains eligibility.</li>"
        "<li>Before / baseline echoes only an explicitly selected observation for the "
        "same subject. It is display context and does not prove the agent caused a change. "
        "Freshness compares exact observed age with max_age_seconds at the supplied "
        "comparison time. Large values are truncated with an explicit marker.</li>"
        "</ul></details>"
    )
    if report.get("schema_version") in (2, 3):
        how_to = how_to.replace(
            "otherwise unobserved.</li>",
            "unconfirmed if the outcome needs an observed change, otherwise unobserved.</li>",
        )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="description" content="Supplied-evidence outcome checks: action '
        'receipt, observed outcome and merged status per requirement.">'
        '<meta name="theme-color" content="#f4f6f5">'
        f"<title>{title} | outcome report</title><style>"
        ":root{color-scheme:light}"
        "body{margin:0;background:#f4f6f5;color:#142c2a;font:17px/1.6 system-ui;"
        "-webkit-tap-highlight-color:transparent}"
        "main{max-width:1280px;margin:auto;padding:40px 32px}"
        "h1{font-size:2.8rem;line-height:1.15;margin:12px 0;text-wrap:balance}"
        "h2,h3{text-wrap:balance}"
        ".eyebrow{letter-spacing:.12em;font-size:.85rem}"
        ".cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}"
        ".card{background:white;border:1px solid #baccc6;border-radius:12px;padding:16px}"
        ".card strong{display:block;font-size:2rem;font-variant-numeric:tabular-nums}"
        ".card span{display:block}"
        "table,caption,tbody{display:block;width:100%}"
        "caption{text-align:left;padding:0 0 12px;color:#405c56}"
        "thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}"
        "tbody{display:grid;gap:16px}"
        "tbody tr{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));"
        "background:#fff;border:1px solid #baccc6;border-radius:14px;overflow:hidden}"
        "td{padding:14px 16px;text-align:left;vertical-align:top;overflow-wrap:anywhere;"
        "min-width:0;font-size:.94rem;border-top:1px solid #e1eae6}"
        "td:before{content:attr(data-label);display:block;font-size:.78rem;"
        "font-weight:700;letter-spacing:.03em;color:#405c56;margin-bottom:5px}"
        ".identity{grid-column:1/4;font-size:1.06rem;font-weight:700;border-top:0}"
        ".st{font-weight:700;border-top:0}.reason{grid-column:3/5}"
        ".st-confirmed{background:#e7f1ec}"
        ".st-contradicted{background:#f9e7e7}"
        ".st-unobserved{background:#f6f0dd}"
        ".metadata{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));"
        "gap:12px 24px;margin:24px 0;font-size:.9rem}"
        ".metadata div{min-width:0}.metadata dt{font-weight:700;color:#405c56}"
        ".metadata dd{margin:3px 0;overflow-wrap:anywhere}"
        ".action-summary,.demo-note{max-width:1000px;overflow-wrap:anywhere}"
        ".downloads{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}"
        ".downloads a{padding:10px 14px;border:1px solid #9bb8ae;border-radius:8px;"
        "background:#fff;font-weight:650}"
        "details{margin:24px 0}summary{cursor:pointer;font-weight:650;padding:8px 0}"
        "pre{background:#fff;padding:20px;border:1px solid #baccc6;"
        "white-space:pre-wrap;overflow-wrap:anywhere}"
        "a{color:#075851}a:hover{text-decoration:underline}"
        ":focus-visible{outline:3px solid #075851;outline-offset:3px}"
        "@media(max-width:700px){main{padding:24px 16px}h1{font-size:2.2rem}"
        ".cards{gap:8px}.card{padding:12px 10px}.card span{font-size:.8rem}"
        ".metadata{grid-template-columns:1fr}"
        "tbody tr{grid-template-columns:repeat(2,minmax(0,1fr))}"
        ".identity{grid-column:1/-1}.st{grid-column:1/-1;border-top:1px solid #e1eae6}"
        ".reason{grid-column:1/-1}td{padding:12px;font-size:.9rem}}"
        '</style></head><body><main><p class="eyebrow">LOCAL EVIDENCE / '
        "REFERENCED OBSERVATIONS</p>"
        f"<h1>{title}</h1><p>Checks supplied evidence, not authenticated execution.</p>"
        + downloads
        + '<div class="cards">'
        + cards
        + "</div>"
        + action_summary
        + comparison
        + table
        + note
        + metadata
        + how_to
        + "<details><summary>Inspect the full JSON report</summary>"
        + "<h2>Inspectable report</h2><pre>"
        + content
        + "</pre></details>"
        "<p>Hashes bind supplied bytes, not authenticity.</p>"
        '<p><a href="https://github.com/alawein/siftgrain-state">Source and installation</a>'
        "</p></main></body></html>"
    )
    from outcome_check._tokens import TOKENS
    from outcome_check.viewer import enhance

    # Unsigned JSON may contain lone surrogates. Show their escapes in every
    # display surface, including the enhanced timeline, without changing data.
    return enhance(page, results, TOKENS).encode("utf-8", errors="backslashreplace").decode("utf-8")
