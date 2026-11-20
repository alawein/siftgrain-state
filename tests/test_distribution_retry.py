import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
spec = importlib.util.spec_from_file_location(
    "distribution", Path(__file__).parents[1] / "scripts/distribute_release.py"
)
assert spec and spec.loader
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


def test_registry_only_404_is_absent(tmp_path, monkeypatch):
    manifest = {"name": "example", "version": "1", "sha256": {"file.whl": "0" * 64}}

    def fail(code):
        def request(*args, **kwargs):
            raise urllib.error.HTTPError("url", code, "failure", {}, None)

        return request

    monkeypatch.setattr(distribution.urllib.request, "urlopen", fail(404))
    assert distribution.registry(manifest, tmp_path) == {"file.whl"}
    monkeypatch.setattr(distribution.urllib.request, "urlopen", fail(403))
    with pytest.raises(urllib.error.HTTPError):
        distribution.registry(manifest, tmp_path)


@pytest.mark.parametrize("change", [None, "inventory", "digest", "download"])
def test_registry_existing_version_requires_exact_downloaded_bytes(tmp_path, monkeypatch, change):
    raw = b"canonical"
    digest = hashlib.sha256(raw).hexdigest()
    manifest = {"name": "example", "version": "1", "sha256": {"file.whl": digest}}
    entry = {
        "filename": "extra.whl" if change == "inventory" else "file.whl",
        "digests": {"sha256": "0" * 64 if change == "digest" else digest},
        "url": "https://files.pythonhosted.org/file.whl",
    }

    def request(url, **kwargs):
        if url.endswith("/json"):
            return io.BytesIO(json.dumps({"urls": [entry]}).encode())
        return io.BytesIO(b"corrupted" if change == "download" else raw)

    monkeypatch.setattr(distribution.urllib.request, "urlopen", request)
    monkeypatch.setattr(distribution, "verify_published_file", lambda *args: None)
    if change:
        with pytest.raises(ValueError):
            distribution.registry(manifest, tmp_path)
    else:
        assert distribution.registry(manifest, tmp_path) == set()
        assert list(tmp_path.iterdir()) == []


def test_github_existing_conflicting_asset_is_never_replaced(tmp_path, monkeypatch):
    directory, assets = tmp_path / "dist", tmp_path / "assets"
    directory.mkdir()
    assets.mkdir()
    (directory / "file.whl").write_bytes(b"canonical")
    uploads, edits = [], []

    def run(arguments, **kwargs):
        if arguments[1] == "api":
            return subprocess.CompletedProcess(
                arguments, 0, json.dumps({"assets": [{"name": "file.whl"}]}), ""
            )
        if arguments[2] == "download":
            Path(arguments[-1], "file.whl").write_bytes(b"old different bytes")
        if arguments[2] == "upload":
            uploads.append(arguments)
        if arguments[2] == "edit":
            edits.append(arguments)
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(distribution.subprocess, "run", run)
    with pytest.raises(ValueError, match="existing GitHub asset differs"):
        distribution.release_upload(directory, assets, "owner/repo", "v1", tmp_path / "notes")
    assert uploads == []
    assert edits == []


def test_partial_registry_verifies_present_then_stages_only_missing(tmp_path, monkeypatch):
    from test_release_artifacts import artifacts

    directory, inventory = artifacts(tmp_path)
    manifest = json.loads(inventory.read_text())
    present, missing = sorted(manifest["sha256"])
    events = []
    entry = {
        "filename": present,
        "digests": {"sha256": manifest["sha256"][present]},
        "url": "https://files.pythonhosted.org/" + present,
    }

    entries = [entry]

    def request(url, **kwargs):
        if url.endswith("/json"):
            return io.BytesIO(json.dumps({"urls": entries}).encode())
        return io.BytesIO((directory / url.rsplit("/", 1)[1]).read_bytes())

    def provenance(manifest, filename, path):
        events.append(filename)
        assert path.read_bytes() == (directory / filename).read_bytes()

    monkeypatch.setattr(distribution.urllib.request, "urlopen", request)
    monkeypatch.setattr(distribution, "verify_published_file", provenance, raising=False)
    missing_files = distribution.registry(manifest, directory)
    assert missing_files == {missing}
    assert events == [present]
    staged = tmp_path / "publisher"
    distribution.stage_missing(manifest, directory, staged, missing_files)
    assert [p.name for p in staged.iterdir()] == [missing]
    assert (staged / missing).read_bytes() == (directory / missing).read_bytes()
    with pytest.raises(ValueError, match="incomplete"):
        distribution.registry(manifest, directory, require_complete=True)
    # Simulate the real publisher: sidecar beside staged artifact, then the missing upload.
    sidecar = staged / (missing + ".publish.attestation")
    sidecar.write_text("{}")
    entries.append(
        {
            "filename": missing,
            "digests": {"sha256": manifest["sha256"][missing]},
            "url": "https://files.pythonhosted.org/" + missing,
        }
    )
    assert distribution.registry(manifest, directory, require_complete=True) == set()
    assert events == [present, present, present, missing]
    assert not list(directory.glob("*.publish.attestation"))


def test_partial_registry_foreign_provenance_never_stages(tmp_path, monkeypatch):
    raw = b"canonical"
    manifest = {
        "name": "example",
        "version": "1",
        "sha256": {"one.whl": hashlib.sha256(raw).hexdigest(), "two.tar.gz": "0" * 64},
    }
    data = {
        "urls": [
            {
                "filename": "one.whl",
                "digests": {"sha256": manifest["sha256"]["one.whl"]},
                "url": "https://files.pythonhosted.org/one.whl",
            }
        ]
    }
    monkeypatch.setattr(
        distribution.urllib.request,
        "urlopen",
        lambda url, **kw: io.BytesIO(json.dumps(data).encode() if url.endswith("/json") else raw),
    )

    def foreign(*args):
        raise ValueError("foreign publisher provenance")

    monkeypatch.setattr(distribution, "verify_published_file", foreign, raising=False)
    with pytest.raises(ValueError, match="foreign publisher"):
        distribution.registry(manifest, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_factual_release_body_has_verified_identity_and_digests():
    manifest = {"name": "example", "version": "1", "sha256": {"file.whl": "a" * 64}}
    body = distribution.release_body(manifest, "owner/repo", "b" * 40, "v1")
    assert "Published" in body and "PyPI" in body
    assert "b" * 40 in body and "a" * 64 in body
    assert "not yet" not in body and "pending" not in body and "prepared" not in body


@pytest.mark.parametrize("fails", [False, True])
def test_github_notes_follow_verified_registry_only(tmp_path, monkeypatch, fails):
    from test_release_artifacts import artifacts

    directory, inventory = artifacts(tmp_path)
    manifest = json.loads(inventory.read_text())
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname="{manifest["name"]}"\nversion="{manifest["version"]}"\n'
    )
    monkeypatch.chdir(tmp_path)
    for key, value in {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF_NAME": "v0.4.0",
        "SOURCE_SHA": "b" * 40,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "distribute_release.py",
            "github",
            "--directory",
            str(directory),
            "--manifest",
            str(inventory),
        ],
    )
    verified = []
    bodies = []

    def registry(*args, require_complete=False):
        assert require_complete
        if fails:
            raise ValueError("publisher provenance failed")
        verified.append(True)
        return set()

    def upload(directory, assets, repository, tag, notes_file):
        assert verified == [True]
        bodies.append(notes_file.read_text())

    monkeypatch.setattr(distribution, "registry", registry)
    monkeypatch.setattr(distribution, "release_upload", upload)
    if fails:
        with pytest.raises(ValueError, match="publisher provenance failed"):
            distribution.main()
        assert bodies == []
    else:
        distribution.main()
        assert len(bodies) == 1
        assert "pending" not in bodies[0] and "not yet" not in bodies[0]
        assert manifest["version"] in bodies[0] and "b" * 40 in bodies[0]
        assert all(digest in bodies[0] for digest in manifest["sha256"].values())


def test_staging_inside_canonical_directory_is_rejected(tmp_path):
    directory = tmp_path / "dist"
    directory.mkdir()
    with pytest.raises(ValueError, match="canonical"):
        distribution.stage_missing({"sha256": {}}, directory, directory / "publisher", set())
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("corrupt_readback", [False, True])
def test_existing_release_notes_update_only_after_complete_readback(
    tmp_path, monkeypatch, corrupt_readback
):
    directory, assets = tmp_path / "dist", tmp_path / "assets"
    directory.mkdir()
    assets.mkdir()
    (directory / "file.whl").write_bytes(b"canonical")
    (assets / "SHA256SUMS").write_bytes(b"checksums")
    notes = tmp_path / "notes.md"
    notes.write_text("Verified published release")
    events = []

    def run(arguments, **kwargs):
        if arguments[1] == "api":
            return subprocess.CompletedProcess(
                arguments, 0, json.dumps({"assets": [{"name": "file.whl"}]}), ""
            )
        operation = arguments[2]
        events.append(operation)
        if operation == "download":
            target = Path(arguments[-1])
            (target / "file.whl").write_bytes(b"canonical")
            if "--pattern" not in arguments:
                (target / "SHA256SUMS").write_bytes(b"wrong" if corrupt_readback else b"checksums")
        if operation == "edit":
            assert events == ["download", "upload", "download", "edit"]
            assert arguments == [
                "gh",
                "release",
                "edit",
                "v1",
                "--repo",
                "owner/repo",
                "--notes-file",
                str(notes),
            ]
            assert notes.read_text() == "Verified published release"
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(distribution.subprocess, "run", run)
    if corrupt_readback:
        with pytest.raises(ValueError, match="uploaded GitHub asset differs"):
            distribution.release_upload(directory, assets, "owner/repo", "v1", notes)
        assert "edit" not in events
    else:
        distribution.release_upload(directory, assets, "owner/repo", "v1", notes)
        assert events[-1] == "edit"
