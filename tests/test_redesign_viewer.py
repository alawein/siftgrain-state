from test_outcomes import packet

from siftgrain_state.core import check_packet
from siftgrain_state.report import render_html


def test_viewer_themes_timeline_and_csp():
    p = packet()
    page = render_html(check_packet(p), p)
    for value in (
        "Cartoon",
        "Calm",
        "Pixel",
        "Lab",
        "Evidence timeline",
        "connect-src",
        "prefers-reduced-motion",
        "webgl2",
        "Pause motion",
        "Appearance",
    ):
        assert value in page
    assert "unsafe-inline" not in page
    assert 'data-status="confirmed"' in page
    assert "localStorage" in page
    assert "innerHTML" not in page


def test_timeline_escapes_evidence_and_noop_label():
    from test_checks_v2 import baseline_packet

    p = baseline_packet()
    p["requirements"][0]["id"] = "<img src=x onerror=alert(1)>"
    page = render_html(check_packet(p), p)
    assert "<img src=x" not in page
    assert "unconfirmed-no-change" in page
