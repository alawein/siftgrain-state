"""Shared conformance vectors; mirrored in eval-audit with import substitutions."""

import os
from pathlib import Path

import pytest

from siftgrain_state import output
from siftgrain_state.report import render_html, render_json


def test_existing_force_and_input_alias(tmp_path):
    source = tmp_path / "input"
    source.write_text("INPUT")
    target = tmp_path / "output"
    target.write_text("OLD")
    with pytest.raises(ValueError, match="output exists"):
        output.validate_outputs([target], [source], False)
    output.validate_outputs([target], [source], True)
    output.atomic_write(target, "NEW\n", True)
    assert target.read_bytes() == b"NEW\n"
    with pytest.raises(ValueError, match="replace input"):
        output.validate_outputs([source], [source], True)
    alias = tmp_path / "alias"
    os.link(source, alias)
    assert output.same_location(source, alias)
    with pytest.raises(ValueError, match="replace input"):
        output.validate_outputs([alias], [source], True)
    assert source.read_text() == "INPUT"


def test_competing_creation(tmp_path, monkeypatch):
    target = tmp_path / "output"
    real_link = os.link

    def compete(stage, destination):
        Path(destination).write_text("COMPETITOR")
        real_link(stage, destination)

    monkeypatch.setattr(os, "link", compete)
    with pytest.raises(FileExistsError):
        output.atomic_write(target, "OURS", False)
    assert target.read_text() == "COMPETITOR"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("force,operation", [(False, "link"), (True, "replace")])
def test_unsupported_publication_fails_closed(tmp_path, monkeypatch, force, operation):
    target = tmp_path / "output"
    if force:
        target.write_text("KEEP")

    def fail(*args):
        raise OSError("unsupported publication")

    monkeypatch.setattr(os, operation, fail)
    with pytest.raises(OSError, match="unsupported"):
        output.atomic_write(target, "NEW", force)
    assert target.read_text() == "KEEP" if force else not target.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_staging_failure_and_second_output_are_per_file(tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    second.write_text("KEEP")
    output.atomic_write(first, "COMPLETED", False)

    def fail(*args):
        raise OSError("staging flush failure")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="staging"):
        output.atomic_write(second, "NEW", True)
    assert first.read_text() == "COMPLETED"
    assert second.read_text() == "KEEP"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["first", "second"]


def test_sorted_finite_json_and_trailing_lf():
    expected = '{\n  "a": [\n    true,\n    null\n  ],\n  "z": 1.5\n}\n'
    assert render_json({"z": 1.5, "a": [True, None]}) == expected
    assert render_json({"a": [True, None], "z": 1.5}) == expected
    for value in [float("nan"), float("inf"), -float("inf")]:
        with pytest.raises(ValueError):
            render_json({"value": value})


def test_html_imported_text_escaping():
    hostile = '<img src=x onerror="alert(1)">&'
    rendered = render_html({"counts": {}, "results": [], "imported": hostile})
    assert hostile not in rendered
    assert "&lt;img" in rendered and "&amp;" in rendered
