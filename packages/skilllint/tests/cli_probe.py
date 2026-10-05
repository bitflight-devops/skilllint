"""Subprocess probe harness for the real ``skilllint`` executable.

Every helper here runs ``skilllint`` the way a user or an agent does: as a child
process, with a pinned environment, and with stdout and stderr captured as raw
bytes. ``typer.testing.CliRunner`` is deliberately not used. It replaces the
streams with in-memory buffers, so it cannot show how Rich decides width and
colour for a real pipe or terminal.

Pinned environment
------------------
Rich reads ``TERM``, ``COLORTERM``, ``NO_COLOR``, ``FORCE_COLOR`` and
``COLUMNS``; the plugin structure validator reads ``CLAUDECODE`` and looks up the
``claude`` binary on ``PATH``; Python's own stream buffering changes the order of
a merged stdout/stderr capture when ``PYTHONUNBUFFERED`` is set. The child
therefore gets an environment built from scratch: ``HOME`` inside the sandbox,
a ``PATH`` that holds only a symlink to ``git`` (gitpython needs it), and one of
the named :data:`ENV_PROFILES`.

Stderr filter
-------------
An editable install computes its version at import time. In a primary checkout
whose ``.git/shallow`` exists, ``vcs_versioning`` then writes a two-line
``UserWarning`` to stderr. It describes the install, not the command, so
:func:`strip_shallow_clone_warning` removes exactly those two lines. Nothing in
this module asserts that stderr is empty.
"""

from __future__ import annotations

import fcntl
import http.server
import io
import json
import os
import pty
import re
import selectors
import shutil
import socket
import struct
import subprocess
import sys
import termios
import threading
import tty
from contextlib import contextmanager
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

EXECUTABLE: Final = Path(sys.executable).parent / "skilllint"
"""The console script of the interpreter running the tests (editable install)."""

DOCS_LAUNCHER: Final = Path(__file__).with_name("docs_cli_launcher.py")
"""Runs the real app with ``SOURCES_DIR`` redirected; see that module."""

# --- environment profiles ---------------------------------------------------

ENV_PROFILES: Final[Mapping[str, Mapping[str, str]]] = {
    "bare": {},
    "xterm256-truecolor": {"TERM": "xterm-256color", "COLORTERM": "truecolor"},
    "dumb": {"TERM": "dumb"},
    "no-color": {"NO_COLOR": "1"},
    "force-color": {"FORCE_COLOR": "1"},
}
"""Variables Rich consults for colour decisions.

Measured on the earlier head: ``TERM=dumb`` changes piped ``check`` output.
``TTY_COMPATIBLE`` and ``TTY_INTERACTIVE`` are not pinned: whether Rich 15 reads
them has not been established.
"""

DEFAULT_COLUMNS: Final = 80
"""Rich's width when ``COLUMNS`` is unset and the stream is not a terminal."""

NARROW_COLUMNS: Final = 30
"""Narrower than the ``rules`` ID column needs, so Rich collapses that table (measured: zero rule IDs shown)."""

WIDE_COLUMNS: Final = 250
"""Wider than every line the commands print, so nothing wraps."""

PTY_ROWS: Final = 24
"""Height of a standard VT100-style terminal; TIOCSWINSZ needs a row count."""

# --- running the executable --------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sandbox:
    """Directories one CLI invocation is allowed to see.

    ``case`` is the working directory. ``HOME`` and the ``bin`` directory live
    beside it, not inside, so a recursive scan of the working directory never
    reports them.
    """

    case: Path
    home: Path
    bin: Path

    @classmethod
    def create(cls, root: Path) -> Sandbox:
        """Create an empty sandbox under *root* with ``git`` linked into ``bin``.

        Returns:
            The new sandbox.

        Raises:
            RuntimeError: When ``git`` is not on the calling process's ``PATH``.
        """
        git = shutil.which("git")
        if git is None:
            msg = "git must be on PATH: the CLI evaluates .gitignore through it"
            raise RuntimeError(msg)
        sandbox = cls(case=root / "case", home=root / "home", bin=root / "bin")
        for directory in (sandbox.case, sandbox.home, sandbox.bin):
            directory.mkdir(parents=True)
        (sandbox.bin / "git").symlink_to(git)
        return sandbox


@dataclass(frozen=True, slots=True)
class CliRun:
    """Outcome of one subprocess run. Streams are raw bytes."""

    returncode: int
    stdout: bytes
    stderr: bytes
    """Empty when the run merged stderr into stdout."""


_SHALLOW_CLONE_WARNING = re.compile(
    rb'^[^\n]*: UserWarning: "[^\n]*" is shallow and may cause errors\n  pre_parse\(wd\)\n', re.MULTILINE
)


def strip_shallow_clone_warning(data: bytes) -> bytes:
    """Remove the two-line ``vcs_versioning`` shallow-clone ``UserWarning``.

    Returns:
        *data* without any occurrence of the warning, matched line for line.
    """
    return _SHALLOW_CLONE_WARNING.sub(b"", data)


def build_env(sandbox: Sandbox, *, profile: str = "bare", columns: int | None = DEFAULT_COLUMNS) -> dict[str, str]:
    """Build the pinned child environment.

    Args:
        sandbox: Supplies ``HOME`` and ``PATH``.
        profile: Key of :data:`ENV_PROFILES`.
        columns: Value for ``COLUMNS``; ``None`` leaves it unset so a pty's
            window size decides the width.

    Returns:
        The complete environment; nothing is inherited from the test process.
    """
    env = {"HOME": str(sandbox.home), "PATH": str(sandbox.bin), **ENV_PROFILES[profile]}
    if columns is not None:
        env["COLUMNS"] = str(columns)
    return env


def _command(args: Sequence[str], docs_sources: Path | None) -> list[str]:
    if docs_sources is None:
        return [str(EXECUTABLE), *args]
    return [sys.executable, "-P", str(DOCS_LAUNCHER), str(docs_sources), *args]


def run_cli(
    args: Sequence[str],
    sandbox: Sandbox,
    *,
    profile: str = "bare",
    columns: int = DEFAULT_COLUMNS,
    tty_stdout: bool = False,
    merge_stderr: bool = False,
    docs_sources: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> CliRun:
    """Run ``skilllint`` once and capture its streams as bytes.

    Args:
        args: Arguments after the program name.
        sandbox: Working directory, ``HOME`` and ``PATH`` for the child.
        profile: Environment profile name from :data:`ENV_PROFILES`.
        columns: Terminal width. Piped runs receive it as ``COLUMNS``; a pty run
            receives it as the window size and ``COLUMNS`` stays unset, so Rich
            has to detect the width itself.
        tty_stdout: Attach stdout to a pty in raw mode. Stderr stays a pipe.
        merge_stderr: Point stderr at the same pipe as stdout, as ``2>&1`` does
            in ``action.yml``. Cannot be combined with ``tty_stdout``.
        docs_sources: When given, run through the docs launcher with this cache
            directory instead of the console script.
        extra_env: Extra variables for the child, applied last.

    Returns:
        The exit status and the captured streams, with the shallow-clone warning
        removed.

    Raises:
        ValueError: When ``tty_stdout`` and ``merge_stderr`` are both set.
    """
    if tty_stdout and merge_stderr:
        msg = "a pty run keeps stderr on its own pipe; merged capture is pipe-only"
        raise ValueError(msg)
    env = build_env(sandbox, profile=profile, columns=None if tty_stdout else columns)
    env.update(extra_env or {})
    command = _command(args, docs_sources)
    if tty_stdout:
        returncode, stdout, stderr = run_on_pty(command, env=env, cwd=sandbox.case, columns=columns)
    else:
        completed = subprocess.run(
            command,
            cwd=sandbox.case,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
            check=False,
        )
        returncode, stdout, stderr = completed.returncode, completed.stdout, completed.stderr or b""
    return CliRun(returncode, strip_shallow_clone_warning(stdout), strip_shallow_clone_warning(stderr))


def run_on_pty(command: list[str], *, env: dict[str, str], cwd: Path, columns: int) -> tuple[int, bytes, bytes]:
    """Run *command* with stdout on a pty and stderr on a pipe.

    Raw mode is set on the slave side before the child starts. Without it the
    line discipline rewrites ``\\n`` to ``\\r\\n`` and the capture would differ
    from a pipe for reasons unrelated to the CLI.

    Returns:
        Exit status, bytes read from the pty, bytes read from the stderr pipe.
    """
    master_fd, slave_fd = pty.openpty()
    try:
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", PTY_ROWS, columns, 0, 0))
        tty.setraw(slave_fd)
        with subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=slave_fd, stderr=subprocess.PIPE
        ) as process:
            os.close(slave_fd)
            slave_fd = -1
            stdout, stderr = _drain(master_fd, process)
            returncode = process.wait()
    finally:
        os.close(master_fd)
        if slave_fd != -1:
            os.close(slave_fd)
    return returncode, stdout, stderr


def _drain(master_fd: int, process: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    """Read the pty and the stderr pipe concurrently until both reach EOF.

    Reading them one after the other can deadlock when the child fills the
    buffer of the stream that is not being read.

    Returns:
        Everything the child wrote to the pty and to stderr.
    """
    if process.stderr is None:
        msg = "process was started without a stderr pipe"
        raise RuntimeError(msg)
    chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    with selectors.DefaultSelector() as selector:
        selector.register(master_fd, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            for key, _ in selector.select():
                name = str(key.data)
                if name == "stdout":
                    try:
                        data = os.read(master_fd, io.DEFAULT_BUFFER_SIZE)
                    except OSError:  # EIO: every writer closed the slave side
                        data = b""
                else:
                    data = os.read(process.stderr.fileno(), io.DEFAULT_BUFFER_SIZE)
                if data:
                    chunks[name].append(data)
                else:
                    selector.unregister(key.fileobj)
    return b"".join(chunks["stdout"]), b"".join(chunks["stderr"])


# --- normalisation -----------------------------------------------------------

LOOPBACK_PORT_PLACEHOLDER: Final = "00000"
"""Five digits: Linux's default ephemeral range (``ip_local_port_range`` 32768-60999) hands out five-digit ports."""
_PORT_DIGITS: Final = len(LOOPBACK_PORT_PLACEHOLDER)
_VERSION = re.compile(r"\d+\.\d+\.\d+(\.dev\d+)?(\+g[0-9a-f]+(\.d\d{8})?)?")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}")
_LOOPBACK_PORT = re.compile(r"127\.0\.0\.1:\d+")
_TEMP_NAME = re.compile(r"tmp[a-z0-9_]{8}(?=\.(?:svg|html))")
_TRACEBACK_FRAMES = re.compile(r'(?:  File "[^\n]*", line \d+(?:, in [^\n]*)?\n(?:    [^\n]*\n)*)+')


def _normalise_version(text: str) -> str:
    """Replace a git-derived version, including the dirty-tree date suffix."""
    return _VERSION.sub("<VERSION>", text)


def _normalise_timestamp(text: str) -> str:
    """Replace the ``YYYY-MM-DD-HHMM`` stamp in cache file names.

    The replacement has the same width, so a Rich panel sized to its content
    keeps its geometry.
    """
    return _TIMESTAMP.sub("0000-00-00-0000", text)


def _normalise_port(text: str) -> str:
    """Replace the loopback server's random port with one of the same width.

    Panels sized to their content change width with the digit count, so
    :func:`loopback_endpoints` only hands out five-digit ports and the
    replacement is five digits too.
    """
    return _LOOPBACK_PORT.sub(f"127.0.0.1:{LOOPBACK_PORT_PLACEHOLDER}", text)


def _normalise_temp_name(text: str) -> str:
    """Replace the random stem ``tempfile.mkstemp`` gives an atomic-write temp file."""
    return _TEMP_NAME.sub("tmp<RAND>", text)


def _collapse_traceback_frames(text: str) -> str:
    """Replace each run of traceback frames with one marker line.

    Frames carry absolute source paths and line numbers, which change whenever a
    later migration step edits the module. The ``Traceback`` header and the
    exception line stay, so the exception type and message are still pinned.
    """
    return _TRACEBACK_FRAMES.sub("  <frames elided>\n", text)


NORMALISERS: Final[Mapping[str, Callable[[str], str]]] = {
    "version": _normalise_version,
    "timestamp": _normalise_timestamp,
    "port": _normalise_port,
    "temp-name": _normalise_temp_name,
    "traceback": _collapse_traceback_frames,
}
"""Opt-in text normalisers, keyed by the names a baseline case lists."""


def normalise(text: str, sandbox: Sandbox, names: Sequence[str]) -> str:
    """Replace per-run values so two runs of unchanged code compare equal.

    Sandbox locations are always replaced, resolved spelling first. The named
    normalisers from :data:`NORMALISERS` then run in the order given.

    Returns:
        The normalised text.
    """
    for label, path in (("<HOME>", sandbox.home), ("<BIN>", sandbox.bin), ("<CASE>", sandbox.case)):
        for spelling in (str(path.resolve()), str(path)):
            text = text.replace(spelling, label)
    for name in names:
        text = NORMALISERS[name](text)
    return text


# --- loopback HTTP server for docs cases -------------------------------------


class _BodyHandler(http.server.BaseHTTPRequestHandler):
    bodies: Mapping[str, bytes] = {}

    def do_GET(self) -> None:
        body = self.bodies.get(self.path)
        if body is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@dataclass(frozen=True, slots=True)
class Endpoints:
    """Base URLs for docs cases, without a trailing slash."""

    served: str
    """A loopback server answering the bodies registered for it."""
    closed: str
    """A loopback port that nothing listens on, so connections are refused."""


@contextmanager
def loopback_endpoints(bodies: Mapping[str, bytes]) -> Iterator[Endpoints]:
    """Serve *bodies* (URL path to content) on loopback and reserve a closed port.

    Yields:
        The served base URL and a refused-connection base URL.
    """
    handler = type("Handler", (_BodyHandler,), {"bodies": dict(bodies)})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        closed_port = reserved.getsockname()[1]
    try:
        for port in (server.server_port, closed_port):
            if len(str(port)) != _PORT_DIGITS:
                msg = f"the OS handed out port {port}; baseline normalisation needs {_PORT_DIGITS}-digit ports"
                raise RuntimeError(msg)
        yield Endpoints(served=f"http://127.0.0.1:{server.server_port}", closed=f"http://127.0.0.1:{closed_port}")
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


# --- golden files ------------------------------------------------------------


class Golden(BaseModel):
    """One recorded behaviour of the CLI: the unit stored under ``baselines/``.

    Golden files are read back through this model, so a hand-edited or
    truncated file fails validation instead of comparing as something else.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    returncode: int
    stdout: str
    stderr: str
    merged_returncode: int | None
    """``None`` for pty variants, which have no merged capture."""
    merged: str | None
    files: dict[str, str | None]
    """Files the case names after the run; ``None`` means the file does not exist."""


def write_golden(path: Path, golden: Golden) -> None:
    """Write *golden* as readable JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(golden.model_dump(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_golden(path: Path) -> Golden:
    """Read and validate a golden file.

    Returns:
        The validated golden.
    """
    return Golden.model_validate_json(path.read_text(encoding="utf-8"))


_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")


def _visible(text: str) -> list[str]:
    """Split into lines with control characters spelled out so a diff can show them."""
    return [_CONTROL.sub(lambda m: f"\\x{ord(m.group()):02x}", line) for line in text.splitlines(keepends=True)]


def describe_difference(expected: Golden, actual: Golden) -> str:
    """Describe how *actual* departs from *expected*.

    Returns:
        An empty string when they are equal, otherwise one unified diff per
        differing field with control characters made visible.
    """
    sections: list[str] = []
    fields = {
        "returncode": (str(expected.returncode), str(actual.returncode)),
        "stdout": (expected.stdout, actual.stdout),
        "stderr": (expected.stderr, actual.stderr),
        "merged_returncode": (str(expected.merged_returncode), str(actual.merged_returncode)),
        "merged": (expected.merged or "", actual.merged or ""),
    }
    for name, (want, got) in fields.items():
        if want != got:
            diff = unified_diff(_visible(want), _visible(got), f"expected {name}", f"actual {name}")
            sections.append("".join(diff) or f"{name}: {want!r} != {got!r}")
    for name in sorted(expected.files.keys() | actual.files.keys()):
        want, got = expected.files.get(name), actual.files.get(name)
        if want != got:
            diff = unified_diff(_visible(want or ""), _visible(got or ""), f"expected {name}", f"actual {name}")
            sections.append("".join(diff) or f"{name}: {want!r} != {got!r}")
    return "\n".join(sections)


# --- help comparison -----------------------------------------------------------

_JSON_OPTION_LINE = re.compile(r"^(\s+)--json(?:\s|$)")


def help_delta(old: str, new: str) -> list[str]:
    """Return the lines *new* adds to *old*; fail loudly on anything else.

    The only default-output change the migration allows is the ``--json`` option
    entry in ``--help``. The permitted shape is: nothing removed, nothing
    changed, and exactly one inserted block. That block must start with a line
    that begins with the option name and may continue on lines indented deeper
    than it (a wrapped description at a narrow width).

    Returns:
        The inserted lines; empty when *old* equals *new*.

    Raises:
        ValueError: When the difference is anything other than that one block.
    """
    old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
    changes = [
        op for op in SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes() if op[0] != "equal"
    ]
    if not changes:
        return []
    if len(changes) != 1 or changes[0][0] != "insert":
        msg = f"help may only gain lines; got {[(tag, old_lines[i1:i2], new_lines[j1:j2]) for tag, i1, i2, j1, j2 in changes]!r}"
        raise ValueError(msg)
    _, _, _, j1, j2 = changes[0]
    inserted = new_lines[j1:j2]
    head = _JSON_OPTION_LINE.match(inserted[0])
    if head is None:
        msg = f"inserted help line does not start with the --json option: {inserted[0]!r}"
        raise ValueError(msg)
    indent = len(head.group(1))
    for continuation in inserted[1:]:
        if len(continuation) - len(continuation.lstrip(" ")) <= indent:
            msg = f"inserted help block holds more than the --json option entry: {inserted!r}"
            raise ValueError(msg)
    return inserted
