"""Console-script names: siftgrain-state is primary; outcome-check stays compatible."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scripts():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)["project"]["scripts"]


def test_primary_names_point_at_the_existing_entrypoints():
    found = scripts()
    assert found["siftgrain-state"] == "siftgrain_state.cli:main"
    assert found["siftgrain-state-mcp"] == "siftgrain_state.mcp:main"


def test_legacy_names_remain_compatible():
    found = scripts()
    assert found["outcome-check"] == found["siftgrain-state"]
    assert found["outcome-check-mcp"] == found["siftgrain-state-mcp"]
    assert found["outcome-convert"] == "siftgrain_state.convert:main"
