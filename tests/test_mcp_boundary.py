import builtins
import io
import json
import socket
import subprocess
from pathlib import Path

from test_outcomes import packet

from siftgrain_state.mcp import serve


def test_mcp_has_no_network_process_or_file_side_effects(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("forbidden side effect")

    for name in ("socket", "create_connection"):
        monkeypatch.setattr(socket, name, deny)
    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, deny)
    monkeypatch.setattr(builtins, "open", deny)
    monkeypatch.setattr(Path, "open", deny)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "check", "arguments": {"packet": packet()}},
    }
    target = io.StringIO()
    serve(io.StringIO(json.dumps(request) + "\n"), target)
    assert json.loads(target.getvalue())["result"]["isError"] is False
