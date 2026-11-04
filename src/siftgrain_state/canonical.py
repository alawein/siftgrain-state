"""RFC 8785 JSON for binary64 numbers; no I/O or optional dependencies."""

import json
import math

from siftgrain_state.contract import InputError, require


def number(value: int | float) -> str:
    """ECMAScript shortest round-trip decimal, with its fixed/exponent thresholds.

    Python's binary64 repr supplies shortest digits, closest to the exact value,
    ties to even. Decimal-point placement below implements ECMAScript 7.1.12.1.
    Integers must convert exactly, avoiding silent signing of a rounded integer.
    """
    try:
        binary = float(value)
    except OverflowError as exc:
        raise InputError("canonical number outside binary64 domain") from exc
    require(math.isfinite(binary), "canonical number must be finite")
    if type(value) is int:
        require(int(binary) == value, "canonical integer must be exactly representable as binary64")
    if binary == 0:
        return "0"
    sign = "-" if binary < 0 else ""
    mantissa, _, exponent = repr(abs(binary)).partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = whole + fraction
    point = len(whole) + (int(exponent) if exponent else 0)
    # Strip leading zeroes while preserving the decimal position.
    leading = len(digits) - len(digits.lstrip("0"))
    point -= leading
    digits = digits.lstrip("0").rstrip("0")
    if 0 < point <= 21:
        body = digits[:point] + ("." + digits[point:] if point < len(digits) else "")
        body += "0" * max(0, point - len(digits))
    elif -6 < point <= 0:
        body = "0." + "0" * -point + digits
    else:
        body = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
        body += "e" + ("+" if point - 1 >= 0 else "-") + str(abs(point - 1))
    return sign + body


def canonicalize(value: object) -> bytes:
    """Canonical UTF-8 JSON; reject unsupported types, Unicode and deep nesting."""

    def string(item: str) -> str:
        try:
            item.encode("utf-16-be")
        except UnicodeError as exc:
            raise InputError("canonical string contains lone surrogate") from exc
        return json.dumps(item, ensure_ascii=False)

    def encode(item: object, depth: int = 0) -> str:
        require(depth <= 32, "canonical JSON nesting exceeds 32")
        if item is None:
            return "null"
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) in (int, float):
            assert isinstance(item, int | float)
            return number(item)
        if type(item) is str:
            return string(item)
        if type(item) is list:
            return "[" + ",".join(encode(child, depth + 1) for child in item) + "]"
        require(type(item) is dict, "unsupported canonical JSON type")
        assert isinstance(item, dict)
        for key in item:
            require(type(key) is str, "canonical keys must be strings")
            string(key)
        keys = sorted(item, key=lambda key: key.encode("utf-16-be"))
        return (
            "{" + ",".join(string(key) + ":" + encode(item[key], depth + 1) for key in keys) + "}"
        )

    return encode(value).encode("utf-8")
