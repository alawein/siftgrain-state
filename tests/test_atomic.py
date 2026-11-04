import json
import os
from pathlib import Path

from test_outcomes import packet

from siftgrain_state.cli import main


def test_atomic_failure_preserves_previous_output(tmp_path, monkeypatch):
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet()))
    target = tmp_path / "report.json"
    target.write_text("KEEP")

    def fail(*args):
        raise OSError("injected replace failure")

    monkeypatch.setattr(os, "replace", fail)
    assert main([str(source), "--json", str(target), "--force"]) == 2
    assert target.read_text() == "KEEP"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["packet.json", "report.json"]


def test_nonforce_creation_race_never_overwrites(tmp_path, monkeypatch):
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet()))
    target = tmp_path / "report.json"
    original = os.link

    def race(stage, destination):
        Path(destination).write_text("RACING WRITER")
        return original(stage, destination)

    monkeypatch.setattr(os, "link", race)
    assert main([str(source), "--json", str(target)]) == 2
    assert target.read_text() == "RACING WRITER"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["packet.json", "report.json"]


def test_stage_write_failure_preserves_target_and_cleans_stage(tmp_path, monkeypatch):
    from siftgrain_state import output

    original = output.tempfile.NamedTemporaryFile
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet()))
    target = tmp_path / "report.json"
    target.write_text("KEEP")

    class BrokenStream:
        def __init__(self, stream):
            self.stream = stream
            self.name = stream.name

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, content):
            self.stream.write(content[:3])
            raise OSError("injected interrupted write")

    def broken(*args, **kwargs):
        return BrokenStream(original(*args, **kwargs))

    monkeypatch.setattr(output.tempfile, "NamedTemporaryFile", broken)
    assert main([str(source), "--json", str(target), "--force"]) == 2
    assert target.read_text() == "KEEP"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["packet.json", "report.json"]
