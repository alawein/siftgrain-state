import io
import json
import os
import subprocess
import sys

import pytest

from outcome_check.mcp import serve


def reply(value):
    out = io.StringIO()
    serve(io.StringIO(value + "\n"), out)
    return json.loads(out.getvalue())


def test_mcp_error_codes():
    assert reply("{")["error"]["code"] == -32700
    assert reply('{"jsonrpc":"2.0","id":1,"method":"unknown"}')["error"]["code"] == -32601
    assert reply('{"jsonrpc":"1.0","id":1,"method":"ping"}')["error"]["code"] == -32600
    assert (
        reply('{"jsonrpc":"2.0","id":1,"method":"tools/list","params":[]}')["error"]["code"]
        == -32602
    )


def test_mcp_supported_version_negotiation():
    response = reply(
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2099-01-01"}}'
    )
    assert response["result"]["protocolVersion"] == "2025-06-18"


def wire_ping(request_id):
    return (
        json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "ping"}, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def native_exchange(data, encoding):
    return subprocess.run(
        [sys.executable, "-m", "outcome_check.mcp"],
        input=data,
        capture_output=True,
        timeout=10,
        check=False,
        env=os.environ | {"PYTHONIOENCODING": encoding},
    )


@pytest.mark.parametrize("encoding", ["cp1252:surrogateescape", "utf-8:surrogateescape"])
def test_native_mcp_preserves_utf8_ids_independent_of_stdio_locale(encoding):
    request_id = "审阅者 😀 �"
    result = native_exchange(wire_ping(request_id), encoding)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert json.loads(result.stdout.decode("utf-8")) == {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {},
    }


@pytest.mark.parametrize("encoding", ["cp1252:surrogateescape", "utf-8:surrogateescape"])
@pytest.mark.parametrize("invalid", [b"\xff", b"\x81", b"\xe2\x82", b"\xc0\xaf"])
def test_native_mcp_rejects_invalid_utf8_and_recovers_next_frame(encoding, invalid):
    malformed = b'{"jsonrpc":"2.0","id":"' + invalid + b'","method":"ping"}\n'
    result = native_exchange(wire_ping(1) + malformed + wire_ping("after 😀"), encoding)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    rows = [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]
    assert len(rows) == 3
    assert rows[0] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert rows[1]["id"] is None
    assert rows[1].get("error", {}).get("code") == -32700
    assert rows[2] == {"jsonrpc": "2.0", "id": "after 😀", "result": {}}


@pytest.mark.parametrize("extra", [0, 1])
def test_mcp_byte_limit_accepts_exact_frame_and_stops_before_oversized_tail(extra):
    # The documented cap counts transport bytes, including the frame's newline.
    limit = 5 * 1024 * 1024
    request = wire_ping("é 😀").rstrip(b"\n")
    frame = request + b" " * (limit - len(request) - 1 + extra) + b"\n"
    target = io.StringIO()
    serve(io.BytesIO(frame + wire_ping(2)), target)
    rows = [json.loads(line) for line in target.getvalue().splitlines()]
    assert rows == (
        []
        if extra
        else [
            {"jsonrpc": "2.0", "id": "é 😀", "result": {}},
            {"jsonrpc": "2.0", "id": 2, "result": {}},
        ]
    )


def test_text_stream_helper_rejects_unencodable_frame_and_recovers():
    target = io.StringIO()
    source = io.StringIO("\udcff\n" + wire_ping(2).decode("utf-8"))
    serve(source, target)
    rows = [json.loads(line) for line in target.getvalue().splitlines()]
    assert rows[0]["id"] is None
    assert rows[0]["error"]["code"] == -32700
    assert rows[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}
