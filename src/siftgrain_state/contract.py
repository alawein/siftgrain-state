import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any


class InputError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InputError(message)


def fields(value: object, keys: set[str], label: str, where: str = "") -> None:
    suffix = f" at {where}" if where else ""
    require(type(value) is dict and set(value) == keys, f"invalid {label} fields{suffix}")


def identifier(value: object, label: str, where: str = "") -> None:
    suffix = f" at {where}" if where else ""
    require(
        isinstance(value, str) and bool(value.strip()) and len(value) <= 200,
        f"invalid {label}{suffix}",
    )


def timestamp(value: str, where: str = "") -> datetime:
    suffix = f" at {where}" if where else ""
    require(type(value) is str and len(value) <= 64, f"invalid timestamp type{suffix}")
    # Restrict to RFC3339 calendar date/time, seconds and explicit zone.
    require(
        bool(
            re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                r"(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
                value,
            )
        ),
        f"timestamp requires RFC3339 timezone{suffix}",
    )
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"invalid timestamp{suffix}") from exc
    require(result.utcoffset() is not None, f"timezone required{suffix}")
    return result


def age_seconds(as_of: str, observed_at: str) -> Fraction:
    """Compare every supplied fractional digit without float rounding."""
    now, observed = timestamp(as_of), timestamp(observed_at)
    delta = now.replace(microsecond=0) - observed.replace(microsecond=0)

    def fraction(value: str) -> Fraction:
        match = re.search(r"\.([0-9]+)", value)
        return Fraction("0." + match[1]) if match else Fraction(0)

    return Fraction(delta.days * 86400 + delta.seconds) + fraction(as_of) - fraction(observed_at)


def json_value(value: object, depth: int = 0, where: str = "") -> None:
    suffix = f" at {where}" if where else ""
    require(depth <= 32, f"JSON nesting exceeds 32{suffix}")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        require(math.isfinite(value), f"nonfinite value{suffix}")
        return
    if type(value) is list:
        for child in value:
            json_value(child, depth + 1, where)
        return
    require(type(value) is dict, f"invalid JSON value{suffix}")
    assert isinstance(value, dict)
    for key, child in value.items():
        identifier(key, "state key", where)
        json_value(child, depth + 1, where)


def validate(packet: dict) -> None:
    require(type(packet) is dict, "invalid packet fields")
    if packet.get("schema_version") in (2, 3):
        validate_v2(packet)
        return
    fields(packet, {"schema_version", "as_of", "requirements", "actions", "observations"}, "packet")
    require(
        type(packet["schema_version"]) is int and packet["schema_version"] == 1,
        "schema_version must be 1",
    )
    timestamp(packet["as_of"])
    definitions = {
        "requirements": {
            "id",
            "subject",
            "path",
            "expected",
            "observation_id",
            "max_age_seconds",
            "action_id",
        },
        "actions": {"id", "status"},
        "observations": {"id", "subject", "observed_at", "state"},
    }
    for name, keys in definitions.items():
        entries = packet[name]
        require(type(entries) is list and len(entries) <= 10000, f"invalid {name} count")
        require(name != "requirements" or bool(entries), "requirements cannot be empty")
        seen = set()
        for index, row in enumerate(entries, 1):
            where = f"{name} row {index}"
            fields(row, keys, name, where)
            identifier(row["id"], name + " ID", where)
            require(row["id"] not in seen, f"duplicate {name} ID at row {index}")
            seen.add(row["id"])
            if name == "actions":
                require(
                    row["status"] in ("succeeded", "failed", "unknown"),
                    f"invalid action status at {where}",
                )
            else:
                identifier(row["subject"], "subject", where)
            if name == "requirements":
                require(
                    type(row["path"]) is list and 0 < len(row["path"]) <= 32,
                    f"invalid path at {where}",
                )
                for key in row["path"]:
                    identifier(key, "path key", where)
                identifier(row["observation_id"], "observation reference", where)
                require(
                    type(row["max_age_seconds"]) is int and row["max_age_seconds"] >= 0,
                    f"invalid max_age_seconds at {where}",
                )
                if row["action_id"] is not None:
                    identifier(row["action_id"], "action reference", where)
                json_value(row["expected"], where=where)
            if name == "observations":
                timestamp(row["observed_at"], where)
                require(type(row["state"]) is dict, f"state must be object at {where}")
                json_value(row["state"], where=where)


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise InputError(f"nonfinite number: {value}")


def load_packet(path: Path) -> tuple[dict, str]:
    with path.open("rb") as stream:
        raw = stream.read(5 * 1024 * 1024 + 1)
    require(len(raw) <= 5 * 1024 * 1024, "input exceeds 5 MiB")
    require(not raw.startswith(b"\xef\xbb\xbf"), "BOM forbidden")
    try:
        packet = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=invalid_constant
        )
        validate(packet)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(str(exc)) from exc
    return packet, hashlib.sha256(raw).hexdigest()


def validate_v2(packet: dict) -> None:
    root = {"schema_version", "as_of", "requirements", "actions", "observations", "baselines"}
    require(root <= set(packet) <= root | {"require_signatures"}, "invalid packet fields")
    require(type(packet["schema_version"]) is int, "invalid schema_version")
    require(type(packet.get("require_signatures", False)) is bool, "invalid require_signatures")
    legacy = {key: packet[key] for key in root - {"baselines"}}
    legacy["schema_version"] = 1
    optional = {"check", "baseline_id", "requires_change"}
    require(type(packet["requirements"]) is list, "invalid requirements count")
    legacy["requirements"] = []
    for index, row in enumerate(packet["requirements"], 1):
        where = f"requirements row {index}"
        require(type(row) is dict, f"invalid requirements fields at {where}")
        check = row.get("check", "equal")
        require(
            check in ("equal", "range", "contains", "regex", "unchanged", "changed_from_baseline"),
            f"invalid check at {where}",
        )
        require(
            type(row.get("requires_change", False)) is bool, f"invalid requires_change at {where}"
        )
        if check in ("unchanged", "changed_from_baseline") or row.get("requires_change", False):
            identifier(row.get("baseline_id"), "baseline reference", where)
        elif "baseline_id" in row:
            identifier(row["baseline_id"], "baseline reference", where)
        if check == "unchanged":
            require(
                not row.get("requires_change", False),
                f"unchanged conflicts with requires_change at {where}",
            )
        if check == "range":
            bounds: dict[str, Any] = row.get("expected")
            require(
                type(bounds) is dict and bool(set(bounds) & {"min", "max"}),
                f"invalid range at {where}",
            )
            require(
                set(bounds) <= {"min", "max", "min_inclusive", "max_inclusive"},
                f"invalid range at {where}",
            )
            for side in ("min", "max"):
                if side in bounds:
                    require(
                        type(bounds[side]) is int
                        or (type(bounds[side]) is float and math.isfinite(bounds[side])),
                        f"numeric range required at {where}",
                    )
                if side + "_inclusive" in bounds:
                    require(
                        side in bounds and type(bounds[side + "_inclusive"]) is bool,
                        f"invalid range inclusivity at {where}",
                    )
            require(
                not ({"min", "max"} <= set(bounds)) or bounds["min"] <= bounds["max"],
                f"reversed range at {where}",
            )
        if check == "regex":
            from siftgrain_state.checks import safe_regex

            safe_regex(row.get("expected"))
        legacy["requirements"].append(
            {key: value for key, value in row.items() if key not in optional}
        )
    legacy["observations"] = []
    for name in ("observations", "baselines"):
        rows = packet[name]
        require(type(rows) is list and len(rows) <= 10000, f"invalid {name} count")
        sanitized = []
        for index, row in enumerate(rows, 1):
            where = f"{name} row {index}"
            require(type(row) is dict, f"invalid {name} fields at {where}")
            if "signature" in row:
                signature = row["signature"]
                keys = {"algorithm", "key_id", "signature"}
                if packet["schema_version"] == 3:
                    keys.add("canonicalization")
                fields(signature, keys, "signature", where)
                if packet["schema_version"] == 3:
                    require(
                        signature["canonicalization"] == "RFC8785",
                        f"unsupported signature canonicalization at {where}",
                    )
                require(
                    signature["algorithm"] == "Ed25519",
                    f"unsupported signature algorithm at {where}",
                )
                identifier(signature["key_id"], "signature key ID", where)
                require(
                    type(signature["signature"]) is str and len(signature["signature"]) <= 128,
                    f"invalid signature encoding at {where}",
                )
            sanitized.append({key: value for key, value in row.items() if key != "signature"})
        if name == "observations":
            legacy["observations"] = sanitized
        else:
            baseline_packet = legacy | {"observations": sanitized}
            validate(baseline_packet)
    validate(legacy)


def migrate_to_v3(packet: dict) -> dict:
    """Copy unsigned v1/v2 input to v3. Signed input needs authentic re-signing."""
    validate(packet)
    require(
        not any(
            "signature" in row
            for name in ("observations", "baselines")
            for row in packet.get(name, [])
        ),
        "signed migration requires authentic re-signing; no signatures are relabeled",
    )
    result = deepcopy(packet)
    result["schema_version"] = 3
    result.setdefault("baselines", [])
    validate(result)
    return result
