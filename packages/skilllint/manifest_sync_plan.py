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


def _replace_bytes(path: Path, content: bytes) -> None:
    """Replace one manifest atomically, retaining its original permission bits."""
    path = path.resolve()
    mode = stat.S_IMODE(path.stat().st_mode)
    descriptor, filename = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    replacement = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content)
        replacement.chmod(mode)
        replacement.replace(path)
    finally:
        replacement.unlink(missing_ok=True)


def _apply_update(update: ManifestUpdate) -> None:
    if update.path.read_bytes() != update.before:
        raise OSError(f"Manifest changed during preparation: {update.path}")
    _replace_bytes(update.path, update.after.encode("utf-8"))


def _restore_update(update: ManifestUpdate) -> None:
    if update.path.read_bytes() != update.after.encode("utf-8"):
        raise OSError(f"Manifest changed after application: {update.path}")
    _replace_bytes(update.path, update.before)


def apply_manifest_updates(updates: Sequence[ManifestUpdate], stage: Callable[[], None] | None = None) -> None:
    """Apply a prepared batch and restore earlier writes if application fails.

    Staging runs only after every file is written. The caller must stage the
    entire batch in one atomic index update. An interrupted process can leave
    complete individual files, so callers must still reconcile on retry even
    when an earlier attempt already advanced a version.
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
