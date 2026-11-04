"""Enforce emitted single-file and shared token byte budgets."""

import gzip
from pathlib import Path

from siftgrain_state._tokens import TOKENS


def main():
    assert Path("design-tokens/tokens.css").read_text(encoding="utf-8") == TOKENS
    for path in Path("site").glob("*.html"):
        size = len(gzip.compress(path.read_bytes(), mtime=0))
        if size > 32768:
            raise ValueError(f"{path.name}: {size} exceeds 32768 gzip bytes")
        print(f"PASS: {path.name} {size}/32768 gzip bytes")


if __name__ == "__main__":
    main()
