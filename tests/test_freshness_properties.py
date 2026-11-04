from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st
from test_outcomes import packet

from siftgrain_state.contract import age_seconds
from siftgrain_state.core import check_packet


@given(st.integers(0, 120), st.integers(0, 999999999), st.integers(-23, 23))
def test_fractional_offset_freshness(seconds, digits, offset):
    as_of = f"2026-10-04T12:02:00.{digits:09}Z"
    sign = "+" if offset >= 0 else "-"
    # Express the same calendar instant in a different zone, with a safe day boundary.
    hour = 12 + offset
    day = 4
    if hour < 0:
        hour += 24
        day -= 1
    elif hour >= 24:
        hour -= 24
        day += 1
    observed = f"2026-10-{day:02}T{hour:02}:00:00.{digits:09}{sign}{abs(offset):02}:00"
    assert age_seconds(as_of, observed) == Fraction(120)
    p = packet()
    p["as_of"] = as_of
    p["observations"][0]["observed_at"] = observed
    p["requirements"][0]["max_age_seconds"] = seconds
    assert check_packet(p)["exit_code"] == (0 if seconds == 120 else 1)


@given(st.integers(1, 10**15 - 1))
def test_submicrosecond_boundary_exact(digits):
    fraction = f"{digits:015}"
    now = "2026-10-04T12:00:00Z"
    later = f"2026-10-04T12:00:00.{fraction}Z"
    assert age_seconds(now, later) == -Fraction(digits, 10**15)
    assert age_seconds(later, now) == Fraction(digits, 10**15)
    p = packet()
    p["requirements"][0]["max_age_seconds"] = 0
    p["observations"][0]["observed_at"] = later
    assert check_packet(p)["results"][0]["reason"] == "future observation"
