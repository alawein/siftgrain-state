from copy import deepcopy

from siftgrain_state.core import check_packet


def test_fault_dataset_has_independent_keys_and_grouped_split():
    import runpy
    from pathlib import Path

    runner = runpy.run_path(str(Path(__file__).parents[1] / "benchmarks/run.py"))
    cases, metrics = runner["cases"], runner["metrics"]
    records = [{"traj": [{"role": "tool", "content": '{"reservation_id":"r","status":"booked"}'}]}]
    rows, keys = cases(records)
    assert len(rows) == 6
    assert len({row["id"] for row in rows}) == 6
    assert not any("gold" in row for row in rows)
    predictions = {r["id"]: check_packet(r["packet"])["results"][0]["status"] for r in rows}
    assert metrics(predictions, keys)["accuracy"] == 1
    noops = [r for r in rows if r["fault"] == "noop"]
    p = deepcopy(noops[0]["packet"])
    p["requirements"][0].pop("requires_change")
    assert check_packet(p)["counts"]["confirmed"] == 1


def test_fault_regression_fails_runner_invariant():
    import runpy
    from pathlib import Path

    import pytest

    runner = runpy.run_path(str(Path(__file__).parents[1] / "benchmarks/run.py"))
    with pytest.raises(AssertionError, match="verdict regression"):
        runner["verify_predictions"]({"x": "confirmed"}, {"x": "unconfirmed"})
