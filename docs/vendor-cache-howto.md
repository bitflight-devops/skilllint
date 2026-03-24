# Vendor Cache How-To Guide

Quick recipes for common documentation caching tasks with `skilllint docs` and the Python API.

## Recipe 1: Cache a documentation page for agent use

**Goal**: Fetch and cache a documentation page so agents can read it from disk.

**Command**:

```bash
skilllint docs fetch "https://code.claude.com/docs/en/hooks.md"
```

**Expected output**:

```
/home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
```

stderr (status):

```
✓ FRESH hooks
```

**Notes**:
- URLs should end in `.md` for most documentation sites (Anthropic, Cursor, etc.)
- The page name is derived from the URL path automatically (e.g. `https://code.claude.com/docs/en/hooks.md` becomes `hooks`)
- The file path is printed to stdout; capture it for use with the Read tool
- Status messages go to stderr: `FRESH`, `REFRESHED`, `UNCHANGED`, `STALE`, or `NEW`

**What to do if it fails**:
- If you see `No Cache Available` panel: no cached copy exists and the network is unavailable. Pre-cache the page before going offline.
- If you see a network error: check your internet connection and URL spelling.


## Recipe 2: Find and read a previously cached page

**Goal**: Locate the most recent cached version of a page, then read its content.

**Step 1**: Find the latest cached file by page name

```bash
skilllint docs latest hooks
```

**Expected output**:

```
/home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
```

**Step 2**: Read the file using the Read tool

Use the path from Step 1 with your Read tool:

```
Read(file_path="/home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md")
```

**Notes**:
- Page names are filesystem-safe names derived from URLs. For `https://code.claude.com/docs/en/hooks.md`, the page name is `hooks`.
- Multiple cached versions may exist with different timestamps. `latest` returns the most recent.
- Exit code 1 if no cached file exists for that page name.


## Recipe 3: Extract a specific section from a large document

**Goal**: Find and extract one section from a multi-section document without reading the entire file.

**Step 1**: View the table of contents

```bash
skilllint docs sections /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
```

**Expected output**:

```
index  level  heading                    lines
-----  -----  -------                    -----
0      0      (preamble)                 1-5
1      1      Overview                   6-20
2      2      Hook input and output      21-50
3      2      Hook validation            51-80
```

**Step 2**: Extract the section by heading text (case-insensitive)

```bash
skilllint docs section /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md "Hook input and output"
```

**Or**: Extract by markdown anchor slug (automatically generated from the heading)

```bash
skilllint docs section /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md "hook-input-and-output"
```

**Expected output**:

```
## Hook input and output
...full section text...
```

**When to use which format**:
- **Heading text**: Use when you know the exact heading from the document. Case doesn't matter; leading `#` is optional.
- **Markdown anchor slug**: Use when you have the GitHub-style slug (lowercase, hyphens replacing spaces and special characters). Useful when anchors are part of documentation links.

**What to do if it fails**:
- If you see `Section not found`: check the exact heading text from the `sections` output or verify the slug format.


## Recipe 4: Force-refresh a stale page

**Goal**: Bypass the time-to-live (TTL) check and always fetch the latest version from the network.

**Command**:

```bash
skilllint docs fetch "https://code.claude.com/docs/en/hooks.md" --force
```

**Expected output**:

```
/home/user/.claude/vendor/sources/hooks-2025-03-24-1530.md
```

stderr (status):

```
✓ REFRESHED hooks
```

**Behavior**:
- `--force` skips the freshness check. A network request is always attempted.
- If content changed: a new timestamped file is written; status is `REFRESHED`.
- If content is identical: the sidecar metadata is updated; status is `UNCHANGED`.
- If network is down even with `--force`: the stale cache is served (status `STALE`).

**Notes**:
- Use `--force` when you need to ensure you have the absolute latest version of a document.


## Recipe 5: Adjust the cache freshness window (TTL)

**Goal**: Control how long a cached page is considered "fresh" before a refresh is needed.

**Cache a page with a custom TTL**:

```bash
skilllint docs fetch "https://code.claude.com/docs/en/hooks.md" --ttl 24.0
```

**Behavior**:
- `--ttl 24.0`: Consider the cache fresh for 24 hours. After 24 hours, the next `fetch` will attempt a network refresh.
- `--ttl 0`: Never cache; always check the network. (Stale cache is still served if the network is unavailable.)
- Default: 4.0 hours

**When to use which TTL**:
- **Stable reference docs** (specs, hook APIs that rarely change): Use `--ttl 24.0` to reduce network calls.
- **Fast-moving docs** (release notes, guides under active editing): Use `--ttl 0` or omit the flag (defaults to 4 hours).

**Notes**:
- TTL only matters when a cached copy already exists. The first fetch always stores the file.
- TTL is per-fetch call; it does not affect previously cached files.


## Recipe 6: Verify a cached file hasn't been modified

**Goal**: Check whether a cached file on disk matches the hash and byte count recorded when it was fetched.

**Command**:

```bash
skilllint docs verify /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
```

**Possible outcomes**:

1. **INTACT** (exit 0):

```
✓ INTACT /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
  sha256: a1b2c3d4e5f6g7h8...
  bytes:  12345
```

The file matches the recorded metadata. Safe to use.

2. **MODIFIED** (exit 1):

```
⚠ MODIFIED — file differs from sidecar
  File:             /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
  Computed sha256:  a1b2c3d4e5f6g7h8...
  Expected sha256:  x9y8z7w6v5u4t3s2...
  Computed bytes:   12345
  Expected bytes:   12000
```

The file has been edited or corrupted. Decide: discard it and re-fetch, or keep the modified version.

3. **UNVERIFIABLE** (exit 1):

```
⚠ UNVERIFIABLE — no sidecar
  File: /home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
  No .meta.json sidecar found — cannot verify this file.
```

No metadata sidecar exists. This can happen if the file was cached before the sidecar system was implemented, or if the sidecar was manually deleted. Re-fetch the file to generate a fresh sidecar.

**What to do for each outcome**:
- **INTACT**: Continue using the file normally.
- **MODIFIED**: If the modifications are intentional, document why. If not, delete the file and re-fetch.
- **UNVERIFIABLE**: Re-fetch with `skilllint docs fetch URL` to create a fresh sidecar.


## Recipe 7: Use the cache when offline

**Goal**: Ensure documentation is available even when the network is unavailable.

**Scenario 1: Cache already exists (most common)**

```bash
skilllint docs fetch "https://code.claude.com/docs/en/hooks.md"
```

**Behavior when offline**:

```
⚠ Serving stale cache — network unavailable
/home/user/.claude/vendor/sources/hooks-2025-03-24-1430.md
```

Exit code 0. A cached copy (even if stale) is served.

**Scenario 2: No cache exists and network is down**

```bash
skilllint docs fetch "https://unknown-site.com/docs/page.md"
```

**Behavior when offline**:

```
✕ No Cache Available
  URL:    https://unknown-site.com/docs/page.md
  Reason: Cannot connect to host
```

Exit code 1. The command fails because there's nothing to serve.

**Pre-cache important documents before going offline**:

```bash
# Cache a batch of documents
for url in \
  "https://code.claude.com/docs/en/hooks.md" \
  "https://docs.anthropic.com/en/docs/claude-code/skills.md" \
  "https://code.claude.com/docs/en/sub-agents.md"
do
  skilllint docs fetch "$url"
done
```

After this loop, all three pages are cached. Offline fetches will serve the cached versions.

**Notes**:
- "Stale" means older than the TTL, not corrupted. Stale cache is still usable.
- The only failure case: no cache exists AND network is down.


## Recipe 8: Use the Python API directly

**Goal**: Integrate the caching system into a Python tool or agent that extends skilllint.

**Basic example**:

```python
from pathlib import Path
from skilllint.vendor_cache import fetch_or_cached, list_sections, read_section

# Fetch or use cache
result = fetch_or_cached("https://code.claude.com/docs/en/hooks.md", ttl_hours=4.0)
print(f"Cache status: {result.status}")
print(f"File: {result.path}")

# Read the file from disk
cached_file = result.path

# List all sections
sections = list_sections(cached_file)
for section in sections:
    print(f"  {section.heading} (lines {section.line_start}-{section.line_end})")

# Extract one section by heading text
content = read_section(cached_file, "Hook input and output")
if content:
    print(content)
else:
    print("Section not found")
```

**Available functions**:

- `fetch_or_cached(url: str, ttl_hours: float = 4.0, force: bool = False) -> CacheResult`
  Returns a CacheResult with `.path`, `.status` (FRESH/REFRESHED/UNCHANGED/STALE/NEW), `.page_name`, and `.url`.

- `list_sections(file_path: Path) -> list[MarkdownSection]`
  Returns MarkdownSection objects with `.heading`, `.level`, `.line_start`, `.line_end`.

- `read_section(file_path: Path, heading: str) -> str | None`
  Returns section text or None. Accepts heading text (case-insensitive) or markdown anchor slug.

- `find_latest(page_name: str) -> Path | None`
  Finds the most recent cached file for a page name, or None.

**Exception handling**:

```python
from skilllint.vendor_cache import NoCacheError

try:
    result = fetch_or_cached("https://example.com/page.md")
except NoCacheError as exc:
    print(f"Cannot fetch {exc.url}: {exc.reason}")
```

Raised when no cache exists and the network is unavailable.

**Notes**:
- Useful for CLI tools that need to fetch and process documentation programmatically.
- The API mirrors the CLI commands; use whichever fits your workflow.


## Recipe 9: Use the standalone script (outside skilllint)

**Goal**: Fetch and cache documentation before skilllint is installed, or in a CI/CD environment where installation isn't complete.

**Command syntax**:

```bash
uv run --script scripts/fetch_doc_source.py fetch "https://code.claude.com/docs/en/hooks.md"
```

**Available commands** (same as `skilllint docs`):

```bash
# Fetch or return cache
uv run --script scripts/fetch_doc_source.py fetch URL

# List sections
uv run --script scripts/fetch_doc_source.py sections FILE

# Extract a section
uv run --script scripts/fetch_doc_source.py section FILE HEADING

# Verify integrity
uv run --script scripts/fetch_doc_source.py verify FILE

# Find latest cached version
uv run --script scripts/fetch_doc_source.py latest PAGE_NAME
```

**When to use the standalone script**:
- Before `skilllint` is installed
- In CI pipelines that don't have the CLI available
- When scripting document capture as part of a larger workflow

**Notes**:
- `scripts/fetch_doc_source.py` is a PEP 723 standalone script.
- It has `[tool.uv.sources]` configured to use the local skilllint package.
- Same commands, same behavior, same cache location as `skilllint docs`.
- Requires `uv` to be installed.
