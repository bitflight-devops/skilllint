"""Real-Git regressions for manifest preparation, rollback, and retry."""

from __future__ import annotations

import json
from pathlib import Path

import git
import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from skilllint import auto_sync_manifests as sync, manifest_sync_plan as plan
from skilllint.boundary.manifest_sync_ingest import decode_marketplace_sync_document, decode_plugin_sync_document


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> git.Repo:
    monkeypatch.chdir(tmp_path)
    repo = git.Repo.init(tmp_path)
    plugin = tmp_path / "plugins/demo/.claude-plugin/plugin.json"
    plugin.parent.mkdir(parents=True)
    plugin.write_text('{"name":"demo","version":"1.0.0","agents":[],"extension":null}')
    marketplace = tmp_path / ".claude-plugin/marketplace.json"
    marketplace.parent.mkdir()
    marketplace.write_text('{"metadata":{"version":"1.0.0"},"plugins":[{"name":"demo","source":"./plugins/demo"}]}')
    readme = tmp_path / "plugins/demo/README.md"
    readme.write_text("Original")
    repo.index.add([str(plugin), str(marketplace), str(readme)])
    actor = git.Actor("Test", "test@example.com")
    repo.index.commit("fixture", author=actor, committer=actor)
    readme.write_text("Changed")
    repo.index.add([str(readme)])
    return repo


def _plugin() -> Path:
    return Path("plugins/demo/.claude-plugin/plugin.json")


def _marketplace() -> Path:
    return Path(".claude-plugin/marketplace.json")


def _assert_synchronized(repo: git.Repo) -> None:
    assert json.loads(_plugin().read_bytes())["version"] == "1.0.1"
    assert json.loads(_marketplace().read_bytes())["metadata"]["version"] == "1.0.1"
    assert json.loads(_plugin().read_bytes())["extension"] is None
    for path in (_plugin(), _marketplace()):
        assert repo.git.show(f":{path}").strip() == path.read_text().strip()


@pytest.mark.parametrize("invalid", ["{", "null", '{"plugins":42}', '{"metadata":{"version":42}}'])
def test_invalid_marketplace_leaves_plugin_and_index_unchanged_then_retry_completes(
    repository: git.Repo, invalid: str
) -> None:
    original_plugin = _plugin().read_bytes()
    original_marketplace = _marketplace().read_bytes()
    staged_plugin = repository.git.show(f":{_plugin()}")
    _marketplace().write_text(invalid)

    with pytest.raises(ValidationError):
        sync._precommit_sync()
    assert _plugin().read_bytes() == original_plugin
    assert repository.git.show(f":{_plugin()}") == staged_plugin

    _marketplace().write_bytes(original_marketplace)
    assert sync._precommit_sync() == 0
    _assert_synchronized(repository)
    first = (_plugin().read_bytes(), _marketplace().read_bytes())
    assert sync._precommit_sync() == 0
    assert (_plugin().read_bytes(), _marketplace().read_bytes()) == first


def test_retry_completes_marketplace_and_staging_after_earlier_plugin_bump(repository: git.Repo) -> None:
    data = json.loads(_plugin().read_bytes())
    data["version"] = "1.0.1"
    _plugin().write_text(json.dumps(data))
    assert sync._precommit_sync() == 0
    _assert_synchronized(repository)


def test_manual_version_bump_does_not_suppress_registration(repository: git.Repo) -> None:
    data = json.loads(_plugin().read_bytes())
    data["version"] = "2.0.0"
    _plugin().write_text(json.dumps(data))
    agent = Path("plugins/demo/agents/new.md")
    agent.parent.mkdir()
    agent.write_text("---\nname: new\ndescription: New agent\n---\n", encoding="utf-8")
    repository.index.add([str(agent), str(_plugin())])

    assert sync._precommit_sync() == 0
    after = json.loads(_plugin().read_bytes())
    assert after["version"] == "2.0.0"
    assert after["agents"] == ["./agents/new.md"]
    assert json.loads(_marketplace().read_bytes())["metadata"]["version"] == "1.0.1"


def test_later_write_failure_rolls_back_earlier_manifest_and_retry_succeeds(
    repository: git.Repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = (_plugin().read_bytes(), _marketplace().read_bytes())
    replace = plan._replace_bytes

    def fail_marketplace(path: Path, content: bytes, *, expected: bytes) -> None:
        if path == _marketplace():
            raise OSError("injected write failure")
        replace(path, content, expected=expected)

    with monkeypatch.context() as fault:
        fault.setattr(plan, "_replace_bytes", fail_marketplace)
        with pytest.raises(OSError, match="injected write failure"):
            sync._precommit_sync()
    assert (_plugin().read_bytes(), _marketplace().read_bytes()) == before
    assert json.loads(repository.git.show(f":{_plugin()}"))["version"] == "1.0.0"
    assert sync._precommit_sync() == 0
    _assert_synchronized(repository)


def test_index_lock_failure_restores_files_and_retry_succeeds(repository: git.Repo) -> None:
    before = (_plugin().read_bytes(), _marketplace().read_bytes())
    lock = Path(repository.git_dir) / "index.lock"
    lock.write_text("another process owns the index")
    with pytest.raises(OSError, match="lock"):
        sync._precommit_sync()
    assert (_plugin().read_bytes(), _marketplace().read_bytes()) == before
    assert lock.read_text() == "another process owns the index"
    lock.unlink()
    assert sync._precommit_sync() == 0
    _assert_synchronized(repository)


def test_malformed_later_plugin_leaves_earlier_plugin_unchanged(repository: git.Repo) -> None:
    before = _plugin().read_bytes()
    later = Path("plugins/zeta/.claude-plugin/plugin.json")
    later.parent.mkdir(parents=True)
    later.write_text("{", encoding="utf-8")
    readme = later.parent.parent / "README.md"
    readme.write_text("Added")
    repository.index.add([str(later), str(readme)])
    with pytest.raises(ValidationError):
        sync._precommit_sync()
    assert _plugin().read_bytes() == before
    assert json.loads(repository.git.show(f":{_plugin()}"))["version"] == "1.0.0"


def test_atomic_write_preserves_symlink_target_and_permissions(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("before")
    link = tmp_path / "manifest.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This environment cannot create symlinks")
    original_mode = target.stat().st_mode
    plan.apply_manifest_updates([plan.ManifestUpdate(link, b"before", "after", "1.0.1")])
    assert link.is_symlink()
    assert target.read_text() == "after"
    assert target.stat().st_mode == original_mode
    assert sorted(path.name for path in tmp_path.iterdir()) == ["manifest.json", "target.json"]


def test_rollback_reports_conflict_without_overwriting_external_edit(tmp_path: Path) -> None:
    target = tmp_path / "plugin.json"
    target.write_text("before")

    def concurrent_edit() -> None:
        target.write_text("external change")
        raise OSError("staging failed")

    with pytest.raises(OSError, match="staging failed") as error:
        plan.apply_manifest_updates([plan.ManifestUpdate(target, b"before", "after", "1.0.1")], concurrent_edit)
    assert target.read_text() == "external change"
    assert any("rollback failed" in note and "plugin.json" in note for note in error.value.__notes__)


@pytest.mark.parametrize("during_rollback", [False, True])
def test_edit_during_temporary_preparation_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, during_rollback: bool
) -> None:
    target = tmp_path / "plugin.json"
    target.write_text("before")
    create_temporary = plan.tempfile.mkstemp
    preparations = 0

    def edit_during_preparation(*, dir: Path, prefix: str) -> tuple[int, str]:  # noqa: A002 - tempfile keyword API
        nonlocal preparations
        result = create_temporary(dir=dir, prefix=prefix)
        preparations += 1
        # The first preparation applies the update; the second restores it.
        if preparations == (2 if during_rollback else 1):
            target.write_text("external change")
        return result

    def fail_staging() -> None:
        raise OSError("staging failed")

    monkeypatch.setattr(plan.tempfile, "mkstemp", edit_during_preparation)
    with pytest.raises(OSError, match="staging failed" if during_rollback else "changed before replacement") as error:
        plan.apply_manifest_updates(
            [plan.ManifestUpdate(target, b"before", "after", "1.0.1")], fail_staging if during_rollback else None
        )
    assert target.read_text() == "external change"
    assert list(tmp_path.iterdir()) == [target]
    if during_rollback:
        assert any("rollback failed" in note for note in error.value.__notes__)


def test_replacement_with_same_bytes_during_preparation_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "plugin.json"
    target.write_text("before")
    create_temporary = plan.tempfile.mkstemp

    def replace_during_preparation(*, dir: Path, prefix: str) -> tuple[int, str]:  # noqa: A002 - tempfile keyword API
        result = create_temporary(dir=dir, prefix=prefix)
        external = tmp_path / "external.json"
        external.write_text("before")
        external.replace(target)
        return result

    monkeypatch.setattr(plan.tempfile, "mkstemp", replace_during_preparation)
    with pytest.raises(OSError, match="changed before replacement"):
        plan.apply_manifest_updates([plan.ManifestUpdate(target, b"before", "after", "1.0.1")])
    assert target.read_text() == "before"
    assert list(tmp_path.iterdir()) == [target]


@given(declaration=st.one_of(st.from_type(str), st.lists(st.from_type(str)), st.none()))
def test_plugin_boundary_preserves_authored_fields(declaration: str | list[str] | None) -> None:
    payload = {"skills": declaration, "extension": {"nested": [None, True, 42, declaration]}}
    document = decode_plugin_sync_document(json.dumps(payload).encode())
    assert document.skills == declaration
    assert document.version == "0.0.0"
    assert json.loads(document.model_dump_json(exclude_unset=True)) == payload


@given(extension=st.one_of(st.from_type(str), st.lists(st.from_type(str)), st.none()))
def test_marketplace_boundary_preserves_nested_extensions(extension: str | list[str] | None) -> None:
    payload = {
        "metadata": {"extension": extension},
        "plugins": [{"name": "demo", "extension": extension}, {"name": "other", "source": None}],
        "extension": extension,
    }
    document = decode_marketplace_sync_document(json.dumps(payload).encode())
    assert document.plugins[0].name == "demo"
    assert document.metadata.version == "0.0.0"
    assert json.loads(document.model_dump_json(exclude_unset=True)) == payload


@pytest.mark.parametrize("content", [b"null", b"[]", b'{"agents":[42]}', b'{"version":null}'])
def test_plugin_boundary_rejects_invalid_sync_shapes(content: bytes) -> None:
    with pytest.raises(ValidationError):
        decode_plugin_sync_document(content)


def test_sync_preserves_extras_nulls_and_absent_defaults(repository: git.Repo) -> None:
    plugin = {"version": "1.0.0", "skills": None, "extension": {"nested": [None, True, 42]}}
    marketplace = {
        "metadata": {"version": "1.0.0", "extension": None},
        "plugins": [{"name": "demo", "extension": {"flag": False}}],
        "extension": [None],
    }
    _plugin().write_text(json.dumps(plugin))
    _marketplace().write_text(json.dumps(marketplace))
    assert sync._precommit_sync() == 0
    plugin["version"] = "1.0.1"
    marketplace["metadata"] = {"version": "1.0.1", "extension": None}
    assert json.loads(_plugin().read_bytes()) == plugin
    assert json.loads(_marketplace().read_bytes()) == marketplace
    for path in (_plugin(), _marketplace()):
        assert json.loads(repository.git.show(f":{path}")) == json.loads(path.read_bytes())


def test_sync_materializes_missing_metadata_without_other_defaults(repository: git.Repo) -> None:
    _marketplace().write_text('{"extension":null}')
    assert sync._precommit_sync() == 0
    assert json.loads(_marketplace().read_bytes()) == {"extension": None, "metadata": {"version": "0.0.1"}}
