"""Prepared manifest writes with rollback before one atomic Git index update."""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestUpdate:
    """One fully prepared document, retaining original bytes for recovery."""

    path: Path
    before: bytes
    after: str
    version: str


def _replace_bytes(path: Path, content: bytes, *, expected: bytes) -> None:
    """Prepare replacement bytes, then recheck the target immediately before replacing."""
    target = path.resolve()
    original_stat = target.stat()
    identity = (original_stat.st_dev, original_stat.st_ino)
    mode = stat.S_IMODE(original_stat.st_mode)
    descriptor, filename = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    replacement = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content)
        replacement.chmod(mode)
        _check_expected_target(path, target, identity, expected)
        replacement.replace(target)
    finally:
        replacement.unlink(missing_ok=True)


def _check_expected_target(path: Path, target: Path, identity: tuple[int, int], expected: bytes) -> None:
    current_stat = path.stat()
    if (
        path.resolve() != target
        or (current_stat.st_dev, current_stat.st_ino) != identity
        or path.read_bytes() != expected
    ):
        raise OSError(f"Manifest changed before replacement: {path}")


def _apply_update(update: ManifestUpdate) -> None:
    _replace_bytes(update.path, update.after.encode("utf-8"), expected=update.before)


def _restore_update(update: ManifestUpdate) -> None:
    _replace_bytes(update.path, update.before, expected=update.after.encode("utf-8"))


def apply_manifest_updates(updates: Sequence[ManifestUpdate], stage: Callable[[], None] | None = None) -> None:
    """Apply a prepared batch and restore earlier writes if application fails.

    Staging runs only after every file is written. The caller must stage the
    entire batch in one atomic index update. An interrupted process can leave
    complete individual files, so callers must still reconcile on retry even
    when an earlier attempt already advanced a version. Expected bytes and target
    identity are checked immediately before replacement. This is optimistic
    conflict detection, not coordination with arbitrary external file writers.
    """
    applied: list[ManifestUpdate] = []
    try:
        for update in updates:
            _apply_update(update)
            applied.append(update)
        if stage is not None:
            stage()
    except BaseException as error:
        recovery_errors: list[str] = []
        for update in reversed(applied):
            try:
                _restore_update(update)
            except OSError as recovery_error:
                recovery_errors.append(f"{update.path}: {recovery_error}")
        if recovery_errors:
            error.add_note(
                "Manifest rollback failed; repair these files before retrying: " + "; ".join(recovery_errors)
            )
        raise
