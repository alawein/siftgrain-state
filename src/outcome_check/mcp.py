"""Small MCP 2025-06-18 stdio transport. No filesystem tool or network listener."""

import json
import sys
from typing import BinaryIO, TextIO

from outcome_check.contract import InputError, invalid_constant, unique_pairs
from outcome_check.core import check_packet


class ProtocolError(ValueError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


LIMIT = 5 * 1024 * 1024
TOOL = {
    "name": "check",
    "description": "Check an explicitly supplied outcome packet offline. Bytes do not prove truth.",
    "inputSchema": {
        "type": "object",
        "properties": {"packet": {"type": "object"}},
        "required": ["packet"],
        "additionalProperties": False,
    },
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


def dispatch(request: dict) -> dict:
    method = request.get("method")
    params = request.get("params", {})
    if type(params) is not dict:
        raise ProtocolError(-32602, "params must be an object")
    if method == "initialize":
        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "outcome-check", "version": "0.5.0.dev0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [TOOL]}
    if method == "tools/call":
        try:
            params = request.get("params", {})
            if type(params) is not dict or params.get("name") != "check":
                raise InputError("unknown tool")
            args = params.get("arguments")
            if type(args) is not dict or set(args) != {"packet"}:
                raise InputError("supply packet only; paths and commands are not supported")
            report = check_packet(args["packet"])
            return {
                "content": [{"type": "text", "text": json.dumps(report, allow_nan=False)}],
                "structuredContent": report,
                "isError": False,
            }
        except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    raise ProtocolError(-32601, "method not found")


def serve(source: TextIO | BinaryIO, target: TextIO) -> None:
    while True:
        line = source.readline(LIMIT + 1)
        if not line:
            return
        request_id = None
        try:
            raw = line.encode("utf-8") if isinstance(line, str) else line
            # Oversized frames end this stream, rather than parsing their tail as requests.
            if len(raw) > LIMIT:
                return
            request = json.loads(
                raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=invalid_constant
            )
            if (
                type(request) is not dict
                or request.get("jsonrpc") != "2.0"
                or type(request.get("method")) is not str
            ):
                raise ProtocolError(-32600, "invalid request")
            if "id" not in request:
                continue
            request_id = request["id"]
            if type(request_id) not in (int, str) and request_id is not None:
                request_id = None
                raise ProtocolError(-32600, "invalid request ID")
            response = {"jsonrpc": "2.0", "id": request_id, "result": dispatch(request)}
        except (ValueError, TypeError, RecursionError, OverflowError) as exc:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": exc.code if isinstance(exc, ProtocolError) else -32700,
                    "message": str(exc),
                },
            }
        target.write(json.dumps(response, allow_nan=False) + "\n")
        target.flush()


def main() -> None:
    serve(sys.stdin.buffer, sys.stdout)


if __name__ == "__main__":
    main()
