import pytest

from siftgrain_state.cli import main


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "packet" in capsys.readouterr().out


def test_primary_and_legacy_entrypoints_share_targets():
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
    pairs = {
        "siftgrain-state": "outcome-check",
        "siftgrain-state-convert": "outcome-convert",
        "siftgrain-state-mcp": "outcome-check-mcp",
    }
    targets = {
        "siftgrain-state": "siftgrain_state.cli:main",
        "siftgrain-state-convert": "siftgrain_state.convert:main",
        "siftgrain-state-mcp": "siftgrain_state.mcp:main",
    }
    for primary, legacy in pairs.items():
        assert scripts[primary] == targets[primary]
        assert scripts[legacy] == targets[primary]
