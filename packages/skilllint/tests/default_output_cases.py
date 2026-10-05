"""Catalogue of CLI invocations whose default output is pinned by golden files.

``test_default_output_unchanged.py`` replays every :class:`Case` here against the
real ``skilllint`` executable and compares the result with the golden stored
under ``baselines/<case id>/<variant id>.json``. ``capture_baselines.py`` writes
those goldens. Both go through :func:`record_case`, so a case is recorded and
checked by the same code.

Every case runs in a fresh sandbox built by its ``setup`` function, with
relative paths and the sandbox as working directory. That keeps absolute
temporary paths out of the output, and lets a ``--fix`` case run twice (separate
and merged capture) without the first run's edits changing the second.

Case selection follows the evidence in the migration brief:

- every command and subcommand, with and without each flag that changes
  rendering, plus the exit-2 and traceback paths;
- the merged ``2>&1`` capture for every case, because ``action.yml`` captures
  that way and a reordering of stderr against stdout is invisible to separate
  captures;
- the full environment-profile, width and pty matrix for :data:`CORE_CASE_IDS`
  only. Those cover every command and docs subcommand and each Rich rendering
  path: help, table, panel, reporter, record export and the docs consoles.
"""

from __future__ import annotations

import subprocess
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cli_probe import (
    DEFAULT_COLUMNS,
    NARROW_COLUMNS,
    WIDE_COLUMNS,
    CliRun,
    Endpoints,
    Golden,
    Sandbox,
    build_env,
    loopback_endpoints,
    normalise,
    run_cli,
)
from docs_cli_launcher import AUTHORITY_URLS_ENV

from skilllint.vendor_io import write_sidecar

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

FIXTURES: Final = Path(__file__).parent / "fixtures" / "claude_code"
BASELINES: Final = Path(__file__).parent / "baselines"

NO_ENDPOINTS: Final = Endpoints(served="", closed="")
"""Stand-in for cases that never contact a server."""

SERVED_TOKEN: Final = "<SERVED>"
CLOSED_TOKEN: Final = "<CLOSED>"
"""Placeholders in docs arguments, replaced by the loopback URLs of the run."""


# --- variants ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Variant:
    """One environment a case is run in."""

    id: str
    profile: str
    columns: int
    tty: bool = False


DEFAULT_VARIANT: Final = Variant("bare-w80", "bare", DEFAULT_COLUMNS)

CORE_VARIANTS: Final = (
    DEFAULT_VARIANT,
    Variant("xterm256-truecolor-w80", "xterm256-truecolor", DEFAULT_COLUMNS),
    Variant("dumb-w80", "dumb", DEFAULT_COLUMNS),
    Variant("no-color-w80", "no-color", DEFAULT_COLUMNS),
    Variant("force-color-w80", "force-color", DEFAULT_COLUMNS),
    Variant("bare-w30", "bare", NARROW_COLUMNS),
    Variant("bare-w250", "bare", WIDE_COLUMNS),
    Variant("pty-xterm256-truecolor-w80", "xterm256-truecolor", DEFAULT_COLUMNS, tty=True),
    Variant("pty-dumb-w80", "dumb", DEFAULT_COLUMNS, tty=True),
)
"""Environment profiles at width 80, the two other widths, and two pty runs."""


# --- workspace builders --------------------------------------------------------

_FIXABLE_SKILL: Final = """\
---
name: fixme
description: >-
  Use when testing. A multiline description for the fixture.
tools:
  - Read
  - Grep
---

# Fixme

Body text.
"""

_AGENT: Final = """\
---
name: helper
description: Use when helping. Does helper things for the plugin tests.
---

Body.
"""

_COMMAND: Final = """\
---
description: Run the thing
---

Do it.
"""

PAGE_MARKDOWN: Final = """\
# Page Title

Intro paragraph.

## Usage

Run the tool. Literal markup stays literal: [bold]x[/bold] [link=http://a]t[/link] :warning:

```bash
# Fenced Fake
```

## Reference

Reference body.
"""
"""LF-only page with two real sections and a fenced pseudo-heading."""

_SEED_STAMP: Final = "2026-01-01-0000"
_SEED_FETCHED_AT: Final = datetime(2026, 1, 1, tzinfo=UTC)
_SEED_URL: Final = "https://example.com/page.md"
"""A sidecar must record an absolute HTTP(S) URL; example.com is reserved for documentation (RFC 2606)."""

STALE_AGE: Final = timedelta(days=1)
"""Older than the 4-hour default ``--ttl`` of ``docs fetch``, so a cache entry this old is refreshed."""

SERVED_BODIES: Final = {
    "/new.md": b"# New page\n\nFresh content.\n",
    "/cached.md": b"# Cached\n\nContent the server serves.\n",
    "/empty.md": b"",
}
"""URL path to body for the loopback server; any other path answers 404."""


def _write(root: Path, relative: str, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _copy_fixture(root: Path, relative: str, fixture: str) -> None:
    _write(root, relative, (FIXTURES / fixture).read_text(encoding="utf-8"))


def workspace(sandbox: Sandbox, _endpoints: Endpoints) -> None:
    """Build the shared tree most ``check`` cases scan."""
    case = sandbox.case
    _copy_fixture(case, "valid_skill.md", "valid_skill.md")
    _copy_fixture(case, "invalid_skill.md", "invalid_skill.md")
    _copy_fixture(case, "invalid-skill/SKILL.md", "invalid-skill/SKILL.md")
    _copy_fixture(case, "plug/.claude-plugin/plugin.json", "valid_plugin.json")
    _copy_fixture(case, "plug/skills/good/SKILL.md", "valid_skill.md")
    _copy_fixture(case, "plug/skills/bad/SKILL.md", "invalid-skill/SKILL.md")
    _write(case, "plug/agents/helper.md", _AGENT)
    _write(case, "plug/commands/run.md", _COMMAND)
    _write(case, "fixme/SKILL.md", _FIXABLE_SKILL)
    _write(case, "failing-examples/fixme/SKILL.md", _FIXABLE_SKILL)
    _write(case, "weird.xyz", "")


def policy_workspace(config: str) -> Callable[[Sandbox, Endpoints], None]:
    """Return a setup whose ``pol/`` tree has a ``.skilllint.json`` holding *config*."""

    def setup(sandbox: Sandbox, endpoints: Endpoints) -> None:
        workspace(sandbox, endpoints)
        _write(sandbox.case, "pol/.skilllint.json", config)
        _copy_fixture(sandbox.case, "pol/x/SKILL.md", "invalid-skill/SKILL.md")

    return setup


def gitignore_workspace(sandbox: Sandbox, endpoints: Endpoints) -> None:
    """Build a git repository whose ``.gitignore`` hides one invalid skill."""
    workspace(sandbox, endpoints)
    _write(sandbox.case, ".gitignore", "ignored/\n")
    _copy_fixture(sandbox.case, "ignored/skill/SKILL.md", "invalid-skill/SKILL.md")
    subprocess.run(
        ["git", "init", "-q"], cwd=sandbox.case, env=build_env(sandbox, columns=None), check=True, capture_output=True
    )


def _seed(
    sandbox: Sandbox,
    page: str,
    *,
    content: str,
    fetched_at: datetime | None,
    url: str = _SEED_URL,
    stamp: str = _SEED_STAMP,
) -> None:
    """Place a cached page, with a sidecar when *fetched_at* is given, in ``sources/``."""
    md_path = sandbox.case / "sources" / f"{page}-{stamp}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(content, encoding="utf-8")
    if fetched_at is not None:
        write_sidecar(md_path, url=url, content=content, fetched_at=fetched_at)


def docs_page(sandbox: Sandbox, _endpoints: Endpoints) -> None:
    """Seed a page with a matching sidecar."""
    _seed(sandbox, "page", content=PAGE_MARKDOWN, fetched_at=_SEED_FETCHED_AT)


def docs_page_modified(sandbox: Sandbox, endpoints: Endpoints) -> None:
    """Seed a page whose bytes no longer match its sidecar."""
    docs_page(sandbox, endpoints)
    path = sandbox.case / "sources" / f"page-{_SEED_STAMP}.md"
    path.write_text(PAGE_MARKDOWN + "Tampered.\n", encoding="utf-8")


def docs_page_unverifiable(sandbox: Sandbox, _endpoints: Endpoints) -> None:
    """Seed a page that has no sidecar."""
    _seed(sandbox, "page", content=PAGE_MARKDOWN, fetched_at=None)


def empty_workspace(_sandbox: Sandbox, _endpoints: Endpoints) -> None:
    """Build nothing; the case needs no files."""


def renamed_folder_workspace(sandbox: Sandbox, _endpoints: Endpoints) -> None:
    """Build a skill folder whose double hyphen makes ``--fix`` rename the folder."""
    _write(sandbox.case, "violations--1/SKILL.md", _FIXABLE_SKILL.replace("fixme", "violations--1"))


def docs_cached(*, age: timedelta, content: str) -> Callable[[Sandbox, Endpoints], None]:
    """Return a setup seeding page ``cached`` fetched *age* ago with *content*."""

    def setup(sandbox: Sandbox, endpoints: Endpoints) -> None:
        _seed(
            sandbox, "cached", content=content, fetched_at=datetime.now(UTC) - age, url=f"{endpoints.served}/cached.md"
        )

    return setup


# --- cases ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Case:
    """One invocation and the environment it needs."""

    id: str
    args: tuple[str, ...]
    setup: Callable[[Sandbox, Endpoints], None] = workspace
    captured: tuple[str, ...] = ()
    """Files read after the run and stored in the golden; absent files are stored as ``None``."""
    normalisers: tuple[str, ...] = ()
    """Names from :data:`cli_probe.NORMALISERS` applied to every stored stream and file."""
    docs: bool = False
    """Run through the docs launcher against a loopback server."""
    authority_urls: tuple[str, ...] | None = None
    """Replacement for the rule registry's authority URLs (docs launcher only)."""
    prints_help: bool = False
    """The output contains a ``--help`` screen, which gains the ``--json`` line."""


_TB: Final = ("traceback",)
_DOCS_FETCH: Final = ("timestamp", "port")
_BAD_URL: Final = "http://[bad/x.md"
"""``urlparse`` rejects this as an invalid IPv6 URL, which no handler in the docs commands expects."""

_CHECK_CASES: Final = (
    # Result rendering: pass, fail, folder, plugin tree.
    Case("check-pass-file", ("check", "valid_skill.md")),
    Case("check-fail-skill-file", ("check", "invalid-skill/SKILL.md")),
    Case("check-fail-skill-folder", ("check", "invalid-skill")),
    Case("check-plugin-dir", ("check", "plug")),
    Case("check-plugin-verbose", ("check", "plug", "--verbose")),
    Case("check-plugin-show-progress", ("check", "plug", "--show-progress")),
    Case("check-plugin-show-summary", ("check", "plug", "--show-summary")),
    Case("check-plugin-no-color", ("check", "plug", "--no-color")),
    Case("check-plugin-all-flags", ("check", "plug", "--verbose", "--show-progress", "--show-summary")),
    Case("check-pass-show-progress", ("check", "valid_skill.md", "--show-progress")),
    Case("check-pass-show-summary", ("check", "valid_skill.md", "--show-summary")),
    Case("check-explicit-check-flag", ("check", "invalid-skill/SKILL.md", "--check")),
    # --fix.
    Case("check-fix-applied", ("check", "fixme/SKILL.md", "--fix"), captured=("fixme/SKILL.md",)),
    Case(
        "check-fix-applied-show-summary",
        ("check", "fixme/SKILL.md", "--fix", "--show-summary"),
        captured=("fixme/SKILL.md",),
    ),
    Case("check-fix-nothing-to-fix", ("check", "valid_skill.md", "--fix")),
    Case(
        "check-fix-failing-examples-path",
        ("check", "failing-examples/fixme/SKILL.md", "--fix"),
        captured=("failing-examples/fixme/SKILL.md",),
    ),
    # Platform and filters.
    Case("check-platform-claude-code", ("check", "plug", "--platform", "claude-code")),
    Case("check-platform-invalid", ("check", "plug", "--platform", "bogus")),
    Case("check-filter-glob", ("check", "plug", "--filter", "**/SKILL.md")),
    Case("check-filter-type-skills", ("check", "plug", "--filter-type", "skills")),
    Case("check-filter-type-invalid", ("check", "plug", "--filter-type", "foo")),
    Case("check-filter-with-filter-type", ("check", "plug", "--filter", "skills/*", "--filter-type", "skills")),
    # Token counts.
    Case("check-tokens-only-single-file", ("check", "valid_skill.md", "--tokens-only")),
    Case("check-tokens-only-skill-folder", ("check", "invalid-skill", "--tokens-only")),
    Case("check-tokens-only-batch", ("check", "valid_skill.md", "invalid-skill/SKILL.md", "--tokens-only")),
    Case("check-tokens-only-plugin-dir", ("check", "plug", "--tokens-only")),
    Case("check-tokens-only-nonexistent", ("check", "nope.md", "--tokens-only"), prints_help=True),
    # Usage errors and the help they print.
    Case("check-no-paths", ("check",), prints_help=True),
    Case("check-nonexistent-path", ("check", "nope.md"), prints_help=True),
    Case("check-unknown-file-type", ("check", "weird.xyz")),
    Case("check-flags-check-and-fix", ("check", "valid_skill.md", "--check", "--fix")),
    Case("check-flags-fix-and-platform", ("check", "valid_skill.md", "--fix", "--platform", "claude-code")),
    # Gitignore.
    Case("check-gitignored-path-skipped", ("check", "ignored/skill/SKILL.md"), setup=gitignore_workspace),
    Case(
        "check-gitignored-path-included",
        ("check", "ignored/skill/SKILL.md", "--include-gitignore"),
        setup=gitignore_workspace,
    ),
    # Policy diagnostics go to stderr beside stdout reporting: the merged capture pins their order.
    Case("check-policy-diagnostic-malformed-config", ("check", "pol/x/SKILL.md"), setup=policy_workspace("{")),
    Case(
        "check-policy-diagnostic-unknown-threshold",
        ("check", "pol/x/SKILL.md", "--show-summary"),
        setup=policy_workspace('{"thresholds": {"bogus": 1}}'),
    ),
)

_CHECK_RECORD_CASES: Final = (
    Case("check-record-svg", ("check", "invalid-skill/SKILL.md", "--record", "out.svg"), captured=("out.svg",)),
    Case("check-record-html", ("check", "invalid-skill/SKILL.md", "--record", "out.html"), captured=("out.html",)),
    Case(
        "check-record-no-color",
        ("check", "invalid-skill/SKILL.md", "--no-color", "--record", "out.svg"),
        captured=("out.svg",),
    ),
    Case(
        "check-record-show-summary",
        ("check", "invalid-skill/SKILL.md", "--show-summary", "--record", "out.svg"),
        captured=("out.svg",),
    ),
    Case(
        "check-record-fix-show-summary",
        ("check", "fixme/SKILL.md", "--fix", "--show-summary", "--record", "out.svg"),
        captured=("out.svg", "fixme/SKILL.md"),
    ),
    Case(
        "check-record-tokens-only",
        ("check", "invalid-skill", "--tokens-only", "--record", "out.svg"),
        captured=("out.svg",),
    ),
    Case("check-record-unknown-file-type", ("check", "weird.xyz", "--record", "out.svg"), captured=("out.svg",)),
    Case(
        "check-record-invalid-platform",
        ("check", "plug", "--platform", "bogus", "--record", "out.svg"),
        captured=("out.svg",),
    ),
    # Defects pinned as they are today: unsupported suffix and unwritable target both raise a traceback, exit 1.
    Case(
        "check-record-unsupported-suffix",
        ("check", "invalid-skill/SKILL.md", "--record", "out.txt"),
        captured=("out.txt",),
        normalisers=_TB,
    ),
    Case(
        "check-record-unwritable-directory",
        ("check", "invalid-skill/SKILL.md", "--record", "missing-dir/out.svg"),
        captured=("missing-dir/out.svg",),
        normalisers=(*_TB, "temp-name"),
    ),
)

_CHECK_DEFECT_CASES: Final = (
    Case(
        "check-fix-renames-folder-then-crashes",
        ("check", "violations--1/SKILL.md", "--fix"),
        setup=renamed_folder_workspace,
        normalisers=_TB,
    ),
)

_RULE_CASES: Final = (
    Case("rules", ("rules",)),
    Case("rules-platform", ("rules", "--platform", "claude-code")),
    Case("rules-category", ("rules", "--category", "frontmatter")),
    Case("rules-severity", ("rules", "--severity", "error")),
    Case("rules-all-filters", ("rules", "-p", "agentskills", "-c", "frontmatter", "-s", "error")),
    Case("rules-no-match", ("rules", "--platform", "cursor", "--category", "codex")),
    Case("rules-severity-invalid", ("rules", "--severity", "bogus")),
    Case("rules-record-svg", ("rules", "--record", "out.svg"), captured=("out.svg",)),
    Case("rules-record-html", ("rules", "--record", "out.html"), captured=("out.html",)),
    Case("rule-known", ("rule", "FM010")),
    Case("rule-known-lowercase", ("rule", "fm010")),
    Case("rule-unknown", ("rule", "ZZ999")),
    Case("rule-missing-argument", ("rule",)),
    Case("rule-record-svg", ("rule", "FM010", "--record", "out.svg"), captured=("out.svg",)),
    Case("rule-record-html", ("rule", "FM010", "--record", "out.html"), captured=("out.html",)),
    Case("rule-unknown-record", ("rule", "ZZ999", "--record", "out.svg"), captured=("out.svg",)),
)

_ROOT_CASES: Final = (
    Case("version-long", ("--version",), normalisers=("version",)),
    Case("version-short", ("-V",), normalisers=("version",)),
    Case("root-no-subcommand", ()),
    Case("root-help", ("--help",), prints_help=True),
    Case("check-help", ("check", "--help"), prints_help=True),
    Case("rules-help", ("rules", "--help"), prints_help=True),
    Case("rule-help", ("rule", "--help"), prints_help=True),
    Case("docs-help", ("docs", "--help"), prints_help=True),
    Case("docs-fetch-help", ("docs", "fetch", "--help"), prints_help=True),
    Case("docs-fetch-authorities-help", ("docs", "fetch-authorities", "--help"), prints_help=True),
    Case("docs-latest-help", ("docs", "latest", "--help"), prints_help=True),
    Case("docs-sections-help", ("docs", "sections", "--help"), prints_help=True),
    Case("docs-section-help", ("docs", "section", "--help"), prints_help=True),
    Case("docs-verify-help", ("docs", "verify", "--help"), prints_help=True),
)

_PAGE: Final = f"sources/page-{_SEED_STAMP}.md"


def _docs(
    case_id: str,
    args: tuple[str, ...],
    setup: Callable[[Sandbox, Endpoints], None] = docs_page,
    normalisers: tuple[str, ...] = ("port",),
) -> Case:
    return Case(case_id, ("docs", *args), setup=setup, docs=True, normalisers=normalisers)


_DOCS_CASES: Final = (
    Case("docs-no-subcommand", ("docs",), setup=docs_page, docs=True, prints_help=True),
    # latest / sections / section / verify read only the seeded cache.
    _docs("docs-latest-found", ("latest", "page")),
    _docs("docs-latest-not-found", ("latest", "absent")),
    _docs("docs-sections", ("sections", _PAGE)),
    _docs("docs-sections-nonexistent-file", ("sections", "absent.md")),
    Case("docs-sections-directory", ("docs", "sections", "sources"), setup=docs_page, docs=True, normalisers=_TB),
    _docs("docs-section-found", ("section", _PAGE, "Usage")),
    _docs("docs-section-found-by-slug", ("section", _PAGE, "#reference")),
    _docs("docs-section-not-found", ("section", _PAGE, "Absent")),
    _docs("docs-section-nonexistent-file", ("section", "absent.md", "Usage")),
    Case(
        "docs-section-directory", ("docs", "section", "sources", "Usage"), setup=docs_page, docs=True, normalisers=_TB
    ),
    _docs("docs-verify-intact", ("verify", _PAGE)),
    _docs("docs-verify-modified", ("verify", _PAGE), setup=docs_page_modified),
    _docs("docs-verify-unverifiable", ("verify", _PAGE), setup=docs_page_unverifiable),
    _docs("docs-verify-nonexistent-file", ("verify", "absent.md")),
    Case("docs-verify-directory", ("docs", "verify", "sources"), setup=docs_page, docs=True, normalisers=_TB),
    # fetch: one case per CacheStatus outcome plus each failure path.
    _docs("docs-fetch-new", ("fetch", f"{SERVED_TOKEN}/new.md"), empty_workspace, _DOCS_FETCH),
    _docs(
        "docs-fetch-fresh",
        ("fetch", f"{CLOSED_TOKEN}/cached.md"),
        setup=docs_cached(age=timedelta(0), content="# Cached\n"),
    ),
    _docs(
        "docs-fetch-refreshed",
        ("fetch", f"{SERVED_TOKEN}/cached.md"),
        setup=docs_cached(age=STALE_AGE, content="# Superseded\n"),
        normalisers=_DOCS_FETCH,
    ),
    _docs(
        "docs-fetch-unchanged",
        ("fetch", f"{SERVED_TOKEN}/cached.md"),
        setup=docs_cached(age=STALE_AGE, content=SERVED_BODIES["/cached.md"].decode()),
    ),
    _docs(
        "docs-fetch-force-refetch",
        ("fetch", "--force", f"{SERVED_TOKEN}/cached.md"),
        setup=docs_cached(age=timedelta(0), content="# Superseded\n"),
        normalisers=_DOCS_FETCH,
    ),
    _docs(
        "docs-fetch-stale",
        ("fetch", f"{CLOSED_TOKEN}/cached.md"),
        setup=docs_cached(age=STALE_AGE, content="# Cached\n"),
    ),
    _docs("docs-fetch-no-cache", ("fetch", f"{CLOSED_TOKEN}/new.md"), setup=empty_workspace),
    _docs("docs-fetch-http-404", ("fetch", f"{SERVED_TOKEN}/missing.md"), setup=empty_workspace),
    _docs("docs-fetch-empty-body", ("fetch", f"{SERVED_TOKEN}/empty.md"), setup=empty_workspace),
    Case(
        "docs-fetch-unexpected-exception",
        ("docs", "fetch", _BAD_URL),
        setup=empty_workspace,
        docs=True,
        normalisers=_TB,
    ),
    # fetch-authorities against a stubbed registry.
    Case(
        "docs-fetch-authorities-all-fetched",
        ("docs", "fetch-authorities"),
        setup=empty_workspace,
        docs=True,
        authority_urls=(f"{SERVED_TOKEN}/new.md", f"{SERVED_TOKEN}/cached.md"),
        normalisers=_DOCS_FETCH,
    ),
    Case(
        "docs-fetch-authorities-mixed-failures",
        ("docs", "fetch-authorities"),
        setup=empty_workspace,
        docs=True,
        authority_urls=(f"{SERVED_TOKEN}/new.md", f"{CLOSED_TOKEN}/down.md", _BAD_URL, f"{SERVED_TOKEN}/missing.md"),
        normalisers=_DOCS_FETCH,
    ),
    Case(
        "docs-fetch-authorities-empty-registry",
        ("docs", "fetch-authorities"),
        setup=empty_workspace,
        docs=True,
        authority_urls=(),
        normalisers=_DOCS_FETCH,
    ),
)

CASES: Final = (*_CHECK_CASES, *_CHECK_RECORD_CASES, *_CHECK_DEFECT_CASES, *_RULE_CASES, *_ROOT_CASES, *_DOCS_CASES)

CORE_CASE_IDS: Final = frozenset({
    "root-help",
    "check-help",
    "rules-help",
    "rules",
    "rule-known",
    "check-fail-skill-file",
    "check-plugin-all-flags",
    "check-nonexistent-path",
    "check-pass-show-summary",
    "check-record-svg",
    "rule-unknown",
    "version-long",
    "docs-verify-intact",
    "docs-verify-modified",
    "docs-sections",
    "docs-section-found",
    "docs-latest-found",
    "docs-fetch-fresh",
    "docs-fetch-no-cache",
    "docs-fetch-authorities-mixed-failures",
})
"""Cases run in every variant: each command and docs subcommand, and each Rich rendering path (help, table, panel,
reporter, record export, docs consoles)."""


def variants_for(case: Case) -> tuple[Variant, ...]:
    """Return the variants *case* is recorded in."""
    return CORE_VARIANTS if case.id in CORE_CASE_IDS else (DEFAULT_VARIANT,)


# --- recording -------------------------------------------------------------------


def _resolve(text: str, endpoints: Endpoints) -> str:
    return text.replace(SERVED_TOKEN, endpoints.served).replace(CLOSED_TOKEN, endpoints.closed)


def case_endpoints(case: Case) -> AbstractContextManager[Endpoints]:
    """Start the loopback server a docs case needs; other cases get :data:`NO_ENDPOINTS`.

    Returns:
        A context manager yielding the endpoints for *case*.
    """
    return loopback_endpoints(SERVED_BODIES) if case.docs else nullcontext(NO_ENDPOINTS)


def run_case(
    case: Case, variant: Variant, root: Path, endpoints: Endpoints, *, merge: bool = False
) -> tuple[Sandbox, CliRun]:
    """Build a fresh sandbox under *root* for *case*, run it once, and return both.

    Returns:
        The sandbox the command ran in (inspect it for files the command wrote)
        and the captured run.
    """
    sandbox = Sandbox.create(root)
    case.setup(sandbox, endpoints)
    extra_env: dict[str, str] = {}
    if case.authority_urls is not None:
        extra_env[AUTHORITY_URLS_ENV] = "\n".join(_resolve(url, endpoints) for url in case.authority_urls)
    run = run_cli(
        [_resolve(arg, endpoints) for arg in case.args],
        sandbox,
        profile=variant.profile,
        columns=variant.columns,
        tty_stdout=variant.tty,
        merge_stderr=merge,
        docs_sources=Path("sources") if case.docs else None,
        extra_env=extra_env,
    )
    return sandbox, run


def _read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def record_case(case: Case, variant: Variant, root: Path, endpoints: Endpoints) -> Golden:
    """Run *case* in *variant* and return what was observed.

    Two fresh sandboxes are used so that a case which edits files (``--fix``)
    behaves identically in the separate and in the merged capture.

    Args:
        case: What to run.
        variant: Environment profile, width and terminal kind.
        root: Empty directory under which the sandboxes are created.
        endpoints: Loopback URLs for docs cases; :data:`NO_ENDPOINTS` otherwise.

    Returns:
        The normalised exit status, streams and captured files.
    """
    sandbox, run = run_case(case, variant, root / "separate", endpoints, merge=False)

    def text(data: bytes, owner: Sandbox) -> str:
        return normalise(data.decode("utf-8"), owner, case.normalisers)

    files = {
        name: None
        if (content := _read_optional(sandbox.case / name)) is None
        else normalise(content, sandbox, case.normalisers)
        for name in case.captured
    }
    merged: str | None = None
    merged_returncode: int | None = None
    if not variant.tty:
        merged_sandbox, merged_run = run_case(case, variant, root / "merged", endpoints, merge=True)
        merged, merged_returncode = text(merged_run.stdout, merged_sandbox), merged_run.returncode
    return Golden(
        returncode=run.returncode,
        stdout=text(run.stdout, sandbox),
        stderr=text(run.stderr, sandbox),
        merged_returncode=merged_returncode,
        merged=merged,
        files=files,
    )


def golden_path(case: Case, variant: Variant) -> Path:
    """Return where the golden for *case* in *variant* is stored."""
    return BASELINES / case.id / f"{variant.id}.json"
