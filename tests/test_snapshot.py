import json
from pathlib import Path

from siftgrain_state.cli import main


def test_committed_snapshot_matches_canonical_inputs(capsys):
    examples = Path(__file__).resolve().parents[1] / "examples"
    assert main([str(examples / "packet.json")]) == 1
    actual = json.loads(capsys.readouterr().out)
    assert actual == json.loads((examples / "report.json").read_text(encoding="utf-8"))
