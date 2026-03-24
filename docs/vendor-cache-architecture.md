# The Vendor Documentation Cache: Architecture and Design

## Overview

The vendor documentation cache is an offline-first system for fetching, storing, and querying external documentation pages. Its purpose is to enable agents to access vendor documentation (Claude hooks, Cursor rules, Copilot configuration, etc.) reliably and efficiently, without relying on real-time network access or delegating documentation retrieval to language model paraphrasing.

This document explains the architectural layers, the problems each layer solves, the key design decisions, and the trade-offs made.

## The Core Problem: Why Cache at All?

When an agent needs to reference external documentation during a task, there are two straightforward approaches that both fail.

**Approach 1: Fetch in real-time via WebFetch or MCP URL-reading tools**

The agent calls a tool that fetches the URL and returns the content directly into context. This sounds efficient until you observe what happens in practice:

- **Information loss through paraphrasing** — URL-reading tools typically pipe content through an AI summarization layer, which loses fidelity. The agent receives a paraphrased version, not the original text. Over multiple queries across a session, this compounds: a paraphrase of a paraphrase.
- **No persistence** — the same documentation page is re-fetched multiple times across different agent invocations, consuming bandwidth and wall-clock time.
- **Network failure blocks work** — if the network is down, the agent cannot proceed, even if the agent only needs a page it read yesterday.
- **Coarse granularity** — the agent must either load an entire documentation page into context (expensive) or load nothing.

**Approach 2: Embed documentation in the skill/agent definition**

Copy the relevant documentation directly into the agent's prompt or skill config. This is maintainable for tiny snippets but fails at scale:

- **Documentation drift** — the embedded copy and the live documentation diverge quickly. A page update goes unnoticed for weeks until a task fails.
- **Configuration bloat** — agent definitions become repositories for vendor documentation, mixing concerns and making config files unreadable.
- **Duplication** — multiple agents need the same documentation, requiring redundant copies.

## Design Principle: Capture Before Consumption

The cache solves these problems by introducing a separation of concerns:

1. **Capture layer** — fetch raw vendor documentation to disk, byte-for-byte identical to what the server returned
2. **Storage layer** — persist the raw content with provenance metadata (URL, timestamp, hash)
3. **Consumption layer** — agents read from disk, with optional section-level extraction

The file on disk is never transformed, summarized, or interpreted at capture time. This preserves fidelity: when an agent reads a cached file, it reads the actual vendor documentation, not a summary of a summary.

## The Five Cache States

The `fetch_or_cached()` function in `packages/skilllint/vendor_cache.py` implements an offline-first strategy that produces one of five possible outcomes:

**FRESH**

The cached file exists and is younger than the TTL (time-to-live) threshold. The file is served immediately from disk without a network request. The sidecar metadata is not updated.

Example: a page cached 2 hours ago with a 4-hour TTL returns `FRESH`.

**REFRESHED**

The cached file exists but is older than the TTL. A network fetch is attempted. The fetch succeeds and the remote content differs from the cached version. A new timestamped file is written. The old file remains on disk.

Example: a page cached 6 hours ago with a 4-hour TTL is refreshed, new content is detected, and a new `page-name-2026-03-24-1630.md` file is written.

**UNCHANGED**

The cached file is older than the TTL. A network fetch is attempted. The fetch succeeds but the remote content is byte-for-byte identical to the cached version (verified by SHA-256 hash). Only the sidecar's `fetched_at` timestamp is updated—no new file is written.

This is an optimization to avoid accumulating duplicate files when vendor documentation hasn't changed.

**STALE**

The cached file exists but is older than the TTL. A network fetch is attempted and fails due to a network error (connection timeout, DNS failure, HTTP 5xx error). The stale cached file is served anyway, with a warning printed to stderr.

This is the core of the offline-first strategy: stale data beats no data.

**NEW**

No cached file exists. A network fetch is attempted. The fetch succeeds, and a new timestamped file is written.

Example: first time the page is ever cached.

## The Offline-First Contract

Only one failure mode is hard: no cache exists **and** the network is unavailable. In this case, the function raises `NoCacheError`.

All other combinations gracefully degrade:

- Cache exists, fresh → serve cache, skip network
- Cache exists, stale, network OK → serve refreshed cache
- Cache exists, stale, network down → serve stale cache (warning)
- Cache missing, network OK → fetch and cache
- Cache missing, network down → raise error

This contract prioritizes availability over freshness. A 6-hour-old cached page is acceptable and better than a network timeout.

## Two Complementary Systems

### System 1: Bulk Vendor Sync (`scripts/fetch_platform_docs.py`)

Runs at session start via a pre-commit hook. Clones or updates a set of predefined vendor repositories and fetches a predefined set of documentation pages.

**What it does:**

- Git clones (shallow) repositories like [anthropics/claude-code](https://github.com/anthropics/claude-code) into `.claude/vendor/{provider}/`
- Fetches predefined HTTP doc-site pages (Cursor rules, Copilot CLI docs) into `.claude/vendor/{provider}/`
- Compares the new content against the previous version (drift detection)
- If changes are detected, writes a drift report to `.claude/vendor/.drift-pending.json`

**Design:**

The script is **declarative** — it defines a fixed set of platforms and pages to sync:

```python
GIT_PLATFORMS = [
    GitPlatform("claude_code", "https://github.com/anthropics/claude-code"),
    GitPlatform("gemini_cli", "https://github.com/google-gemini/gemini-cli"),
    # ...
]

DOC_SITE_PLATFORMS = [
    DocSitePlatform("cursor", [
        DocPage("https://cursor.com/docs/context/rules", "rules.md"),
    ]),
    # ...
]
```

When changes are detected, drift is recorded so that review and schema updates can be triggered downstream.

### System 2: On-Demand Page Capture (`skilllint docs` CLI)

Invoked by agents during task execution via `skilllint docs fetch URL` (or `uv run --script scripts/fetch_doc_source.py fetch URL` before skilllint is installed).

**What it does:**

- Fetches a single documentation page by URL
- Derives a filesystem-safe page name from the URL path
- Stores the page in `.claude/vendor/sources/{page-name}-{timestamp}.md`
- Returns the file path to stdout so the agent can read it with the Read tool

**Design:**

This system is **dynamic** — any URL can be cached on-demand. There's no predefined list. An agent can request:

```
skilllint docs fetch https://docs.anthropic.com/en/docs/build-with-claude/agents
skilllint docs fetch https://github.com/some/repo/raw/main/ARCHITECTURE.md
```

The CLI interprets the URL, derives a safe page name, checks cache freshness, and either serves the cached file or fetches a new copy.

### Shared Foundation (`packages/skilllint/vendor_io.py`)

Both systems and the user-facing CLI build on a shared library of low-level I/O utilities:

- `sha256_hex()` — compute full SHA-256 hash of text
- `fetch_url_text()` — HTTP client with timeout and redirect handling
- `read_text_or_none()` — safe UTF-8 file read
- `write_sidecar()` — write `.meta.json` metadata file
- `load_sidecar()` — load and parse `.meta.json`
- `write_json()` and `load_json_or_none()` — JSON persistence with standard formatting

This shared foundation is also used by `scripts/fetch_spec_schema.py` for schema drift detection, ensuring consistent hashing and I/O behavior across the entire vendor sync ecosystem.

## File Organization and Naming

Cached files live in `.claude/vendor/sources/`, named with the pattern:

```
{page-name}-{YYYY-MM-DD-HHMM}.md
```

Example filenames:

- `claude-code--settings-2026-03-24-1430.md` (from `https://docs.anthropic.com/en/docs/claude-code/settings.md`)
- `context--rules-2026-03-24-1100.md` (from `https://cursor.com/docs/context/rules.md`)
- `sub-agents-2026-03-23-0900.md` (from `https://code.claude.com/docs/en/sub-agents.md`)

The `derive_page_name()` function implements the naming algorithm:

1. Extract the URL path component
2. Strip common prefixes like `/en/`, `/docs/`, `/api/`
3. Remove the `.md` extension
4. Join remaining path segments with `--`
5. Replace any non-alphanumeric-or-hyphen character with a hyphen

**Why this naming convention?**

- Timestamps sort lexicographically, enabling the `find_latest()` function to locate the most recent file with a simple max() comparison
- Page names are human-readable, so `.claude/vendor/sources/` remains navigable in a file browser
- Granularity is minutes, not seconds, keeping filenames readable while avoiding sub-minute refetch scenarios

## Sidecar Metadata Model

Alongside each cached markdown file sits a `.meta.json` sidecar:

```json
{
  "url": "https://docs.anthropic.com/en/docs/claude-code/settings.md",
  "fetched_at": "2026-03-24T14:30:00+00:00",
  "sha256": "abc123...",
  "byte_count": 4821
}
```

**Why a sidecar instead of a central database?**

- **Atomicity** — writing a single file is atomic. A sidecar and its corresponding markdown file always stay in sync; no locking or transaction logic needed.
- **Portability** — the cache directory can be copied, synced, or committed to git without needing to export/import a database.
- **Discoverability** — looking at the file system reveals everything: file paths show when pages were cached, sidecars show their provenance.
- **Resilience** — accidental deletion of a file doesn't orphan metadata in a database; the sidecar is deleted too. Partial deletions (file exists but sidecar missing) are detectable.

**Integrity verification:**

The `verify_integrity()` function reads a file and computes its current SHA-256 hash and byte count, then compares against the sidecar. Three outcomes are possible:

- **INTACT** — hashes and byte counts match
- **MODIFIED** — the file has been edited or corrupted
- **UNVERIFIABLE** — no sidecar exists (cannot establish expected values)

This enables agents or maintainers to detect if a cached file has been accidentally modified, corrupted, or deleted.

## Section Decomposition with marko

When an agent needs only a portion of a cached page, the `list_sections()` and `read_section()` functions allow section-level extraction.

**The problem with regex-based heading detection:**

A naive approach uses regex to find lines like `^#+` (one or more hashes followed by a space). This fails catastrophically inside fenced code blocks:

````markdown
## How to use hooks

```bash
# This line starts with a hash and space
echo "Does this count as a heading?"
```

## Actually, that's a mistake
````

The regex sees three headings when there are only two. The solution requires understanding markdown structure, not just pattern matching.

**The hybrid approach:**

The cache uses a two-phase decomposition:

1. **Parse the AST** — the `marko` library parses the markdown into an abstract syntax tree (AST), correctly identifying ATX headings while respecting fenced code block boundaries.

2. **Map back to source lines** — the AST gives accurate heading texts and relative order, but not source line numbers (the AST discards that information). A second pass scans the source line-by-line, tracking code fence state (in or out of a fence), and matches headings by level and position.

```python
def _extract_ast_headings(text: str) -> list[tuple[int, str]]:
    """Extract (level, heading_text) from marko AST."""
    doc = marko.parse(text)
    result = []
    for child in doc.children:
        if isinstance(child, MarkoHeading):
            # Extract inline text from heading
            parts = []
            for inline in child.children:
                raw = getattr(inline, "children", "")
                parts.append(raw if isinstance(raw, str) else str(raw))
            result.append((child.level, "".join(parts).strip()))
    return result
```

This gives correct heading detection even when code blocks contain lines that look like headings.

**Heading text matching:**

The `read_section()` function accepts two query formats for finding sections:

- **Heading text** (case-insensitive): `"Hook input and output"`
- **Markdown anchor slug** (GitHub/GitLab compatible): `"hook-input-and-output"`

Both are normalized and compared, enabling agents to query by either format. The slug function mirrors GitHub's slug generation: lowercase, strip non-word characters (except hyphens and spaces), collapse whitespace/hyphens to single hyphens.

## TTL and Freshness: The 4-Hour Default

The default cache TTL is 4 hours. This value was chosen to balance several factors:

- **Captures a work session** — most agent tasks complete within a few hours. A 4-hour TTL means agents are unlikely to re-fetch pages during a single session.
- **Reflects documentation change frequency** — vendor documentation changes infrequently during business hours. A 6-hour-old page is still valid 99% of the time.
- **Accounts for time zones** — a 4-hour TTL tolerates moderate time zone drift in logs and timestamps.

The TTL is configurable per-call (`fetch_or_cached(url, ttl_hours=6.0)`), but 4 hours is the default for manual CLI invocations and the value used by agents.

## Trade-Offs

### File Accumulation vs. Automatic Pruning

The cache does not automatically delete old files. Every `REFRESHED` status creates a new file; old files remain on disk.

**Why?**

Disk space is cheap for text documentation. A cached GitHub markdown file is typically 5-20 KB. Even after 1,000 fetches (200 MB), the cost is negligible for development environments. Meanwhile, file accumulation provides audit trail benefits: you can see when a page was last cached and how its contents changed over time.

**The trade-off:**

- **Pro** — no locking, no cleanup logic, no race conditions during concurrent access
- **Con** — directory grows unbounded; manual cleanup may eventually be needed (or a future pruning policy)

### marko as a Runtime Dependency

The cache adds `marko` to skilllint's dependencies. This is a non-trivial dependency (not from stdlib).

**Why add it?**

Correct markdown section extraction requires parsing, not regex. Regex-based approaches fail on code fences, inline code, and edge cases. marko is a lightweight, well-maintained markdown parser. The dependency adds ~10 KB of library code and handles a core requirement correctly.

**The alternative:**

Write a custom markdown parser in skilllint. This would be hundreds of lines of error-prone code to handle edge cases that marko already solves.

**The trade-off:**

- **Pro** — correct parsing, maintainable code, vendor-tested library
- **Con** — additional dependency, potential version conflicts

### PEP 723 Local Path Dependency

The standalone `scripts/fetch_doc_source.py` script declares skilllint as a local path dependency via PEP 723:

```python
# /// script
# dependencies = ["typer>=0.21.0", "httpx>=0.27.0", "skilllint"]
# [tool.uv.sources]
# skilllint = { path = ".." }
# ///
```

This allows the script to be invoked with `uv run --script scripts/fetch_doc_source.py` before skilllint is installed globally, without duplicating the I/O utilities.

**Why this approach?**

- Agents can cache documentation before skilllint is installed
- No code duplication; the script uses the same `vendor_cache` module as the CLI
- PEP 723 with uv handles dependency resolution transparently

**The trade-off:**

- **Pro** — single source of truth for cache logic, works in any environment with uv
- **Con** — requires uv; doesn't work with pip-only environments (though skilllint itself uses uv)

### Timestamp Granularity: Minutes, Not Seconds

Filenames use `YYYY-MM-DD-HHMM` format, with one-minute granularity. Sub-minute refetches are not distinguished.

**Why not seconds?**

- Filenames remain readable: `claude-code--settings-2026-03-24-1430.md` is clearer than `claude-code--settings-2026-03-24-143047.md`
- Simultaneous fetches within the same minute are rare enough not to require nanosecond precision
- The performance difference between sub-second and sub-minute granularity is not meaningful for documentation

## Failure Modes and Error Handling

### Network Unavailable, No Cache

```
skilllint docs fetch https://docs.anthropic.com/en/docs/claude-code/settings.md
# → NoCacheError (exit 1)
```

This is the only hard failure. When offline and the page has never been cached, work cannot proceed.

### Network Unavailable, Cache Exists

```
skilllint docs fetch https://docs.anthropic.com/en/docs/claude-code/settings.md
# → Serving stale cache from 6 hours ago
# → STALE status (exit 0 with warning to stderr)
```

The agent receives the file path and can proceed.

### Network OK, Content Changed

The new content is fetched, written to a new timestamped file, and the sidecar is written alongside it. The old file remains.

### Network OK, Content Unchanged

The sidecar's `fetched_at` timestamp is updated (the file is "touched"), but no new markdown file is written.

### Malformed or Unparseable URL

`derive_page_name()` may produce an empty or unintelligible page name from a malformed URL. This is not validated before fetching. The fetch itself will fail (404 or similar HTTP error), and `NoCacheError` is raised if no cache exists.

## Integration Points

### Agents Using the Cache

An agent that needs to reference vendor documentation follows this flow:

1. Invoke `skilllint docs fetch URL` (or the standalone script)
2. Capture the printed file path
3. Use the Read tool on that file path
4. For large files, use `skilllint docs sections FILE` to find relevant sections
5. Use `skilllint docs section FILE HEADING` to extract just the needed section

### CI and Hooks

The `scripts/fetch_platform_docs.py` script is invoked at session start via a pre-commit hook. If drift is detected, a report is written and the hook exits with code 2, signaling that schema updates may be needed.

### Verification and Auditing

The `skilllint docs verify FILE` command allows CI or manual checks to ensure that cached files have not been accidentally modified.

## Summary

The vendor documentation cache is a layered system designed to:

1. **Preserve fidelity** — raw documentation is captured to disk, never paraphrased
2. **Enable offline work** — stale cache is always better than network failure
3. **Support agents efficiently** — section-level extraction avoids loading entire pages
4. **Provide auditability** — sidecar metadata and file accumulation create an audit trail
5. **Keep complexity low** — shared utilities, atomic file operations, no custom locking

The design separates concerns: bulk sync handles predefined platforms and drift detection; on-demand fetch handles dynamic URLs; agents read from disk with optional section extraction. The shared I/O foundation ensures consistency across all three.
