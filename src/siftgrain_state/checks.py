"""Bounded fixed-width patterns, without backtracking ambiguity."""

import re

from siftgrain_state.contract import require


def safe_regex(pattern: object) -> re.Pattern[str]:
    require(type(pattern) is str and 2 <= len(pattern) <= 256, "invalid regex length")
    assert isinstance(pattern, str)
    require(pattern.startswith("^") and pattern.endswith("$"), "regex must be anchored")
    assert isinstance(pattern, str)
    body = pattern[1:-1]
    index, width = 0, 0
    while index < len(body):
        char = body[index]
        if char == "[":
            end = body.find("]", index + 1)
            require(end > index + 1, "invalid regex class")
            contents = body[index + 1 : end]
            require(bool(re.fullmatch(r"[A-Za-z0-9 _-]+", contents)), "unsafe regex class")
            index = end + 1
        elif char == "\\":
            require(
                index + 1 < len(body) and body[index + 1] in ".-_^$[]{}\\", "unsafe regex escape"
            )
            index += 2
        else:
            require(char.isascii() and (char.isalnum() or char in " _-:/,@"), "unsafe regex token")
            index += 1
        count = 1
        if index < len(body) and body[index] == "{":
            end = body.find("}", index + 1)
            require(end != -1, "invalid regex repetition")
            digits = body[index + 1 : end]
            require(bool(re.fullmatch(r"[0-9]{1,3}", digits)), "fixed repetition required")
            count = int(digits)
            require(1 <= count <= 128, "regex repetition exceeds 128")
            index = end + 1
        width += count
        require(width <= 4096, "regex width exceeds 4096")
    try:
        return re.compile(pattern)
    except re.error as exc:
        from siftgrain_state.contract import InputError

        raise InputError("invalid regex") from exc
