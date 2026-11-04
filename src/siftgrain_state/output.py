"""Atomic local exports; identical helpers are mirrored in eval-audit."""

import os
import tempfile
from pathlib import Path


def same_location(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True
    return left.exists() and right.exists() and left.samefile(right)


def validate_outputs(outputs: list[Path], inputs: list[Path], force: bool) -> None:
    for index, path in enumerate(outputs):
        if any(same_location(path, prior) for prior in outputs[:index]):
            raise ValueError("output paths must differ")
        if any(same_location(path, source) for source in inputs):
            raise ValueError("output cannot replace input")
        if not force and path.exists():
            raise ValueError(f"output exists: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"missing output directory: {path.parent}")


def atomic_write(path: Path, content: str, force: bool) -> None:
    stage: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stage = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if force:
            os.replace(stage, path)
        else:
            os.link(stage, path)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
