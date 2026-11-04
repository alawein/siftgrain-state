import builtins
import io
import json
import os
import socket
import subprocess
from pathlib import Path

import pytest
from test_outcomes import packet

from siftgrain_state.cli import main
from siftgrain_state.core import check_packet
from siftgrain_state.report import render_html, render_json


def test_runtime_cannot_collect_execute_or_write_other_paths(tmp_path, monkeypatch, capsys):
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet()))
    before = source.read_bytes()
    target = tmp_path / "report.json"
    from test_signatures import signed_packet

    signed, verifier = signed_packet()
    signed["require_signatures"] = True
    unsigned = signed | {"require_signatures": False}
    unsigned["observations"] = [
        {key: value for key, value in signed["observations"][0].items() if key != "signature"}
    ]

    check_packet(packet())
    render_html(check_packet(packet()), packet())
    render_json(check_packet(packet()))
    from siftgrain_state.contract import migrate_to_v3
    from siftgrain_state.signatures import sign_observation

    v3 = migrate_to_v3(unsigned)
    v3["observations"][0]["state"]["float"] = 1.5
    v3["observations"][0] = sign_observation(
        v3["observations"][0], "fixture", bytes(range(32)), canonicalization="RFC8785"
    )
    v3["require_signatures"] = True
    # Load optional crypto before denying external operations.
    assert check_packet(v3, verifier)["exit_code"] == 0
    open_builtin, open_io = builtins.open, io.open
    os_open = os.open

    def denied(*args, **kwargs):
        raise AssertionError("forbidden collector or executor")

    def allowed(path):
        name = Path(path)
        return name == target or (
            name.parent == tmp_path
            and name.name.startswith(".report.json.")
            and name.suffix == ".tmp"
        )

    def guard(original):
        def call(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                assert allowed(path) or (Path(path) == tmp_path and "opener" in kwargs), (
                    f"undeclared write {path}"
                )
            return original(path, mode, *args, **kwargs)

        return call

    def guarded_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            assert allowed(path), f"undeclared os.open write {path}"
        return os_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(socket, "socket", denied)
        patch.setattr(socket, "create_connection", denied)
        patch.setattr(subprocess, "Popen", denied)
        patch.setattr(subprocess, "run", denied)
        patch.setattr(os, "system", denied)
        patch.setattr(builtins, "open", guard(open_builtin))
        patch.setattr(io, "open", guard(open_io))
        patch.setattr(os, "open", guarded_os_open)
        assert check_packet(v3, verifier)["exit_code"] == 0
        assert check_packet(signed, verifier)["exit_code"] == 0
        assert check_packet(unsigned)["exit_code"] == 0
        assert main([str(source)]) == 0
        assert main([str(source), "--json", str(target)]) == 0
    assert source.read_bytes() == before
    assert json.loads(target.read_text())["exit_code"] == 0
    assert "confirmed" in capsys.readouterr().out


def test_packet_cannot_specify_executor_or_collector():
    from siftgrain_state.contract import InputError

    p = packet()
    p["collector"] = "https://example.invalid"
    with pytest.raises(InputError):
        check_packet(p)
