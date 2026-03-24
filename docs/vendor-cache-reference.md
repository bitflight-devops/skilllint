# Vendor Cache Reference

Reference documentation for offline-first documentation caching and section queries. Complete technical specifications for function signatures, parameters, return types, exit codes, and file formats.

## CLI: `skilllint docs`

The `skilllint docs` subcommand group provides five commands for fetching, querying, and verifying cached vendor documentation. All commands support both TTL-based freshness and offline fallback.

### fetch

Fetch a documentation page or return a cached copy. Implements offline-first behavior: returns fresh cache without network requests, refreshes stale cache on network availability, and serves stale cache when network is unavailable.

**Synopsis**

```
skilllint docs fetch <URL> [--ttl HOURS] [--force]
```

**Arguments**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `URL` | string | yes | Full documentation URL to fetch or look up in cache |

**Options**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `--ttl` | float | 4.0 | Cache time-to-live in hours before a refresh is attempted |
| `--force` | flag | False | Skip the freshness check and always attempt a network fetch |

**Output**

- **stdout**: Path to the cached file (one per line, suitable for shell capture)
- **stderr**: Status message (`FRESH`, `REFRESHED`, `UNCHANGED`, `STALE`, or `NEW`)

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | Success (file found or fetched) |
| 1 | No cached copy exists and network is unavailable |

### latest

Find the most recent cached file for a given page name.

**Synopsis**

```
skilllint docs latest <PAGE_NAME>
```

**Arguments**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `PAGE_NAME` | string | yes | Filesystem-safe page name (e.g. `claude-code--settings`); use `derive_page_name()` to generate from a URL |

**Output**

- **stdout**: Path to the cached file
- **stderr**: Error message if not found

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | File found |
| 1 | No cached file exists for the given page name |

### sections

Print a plain-text table of sections in a cached markdown file.

**Synopsis**

```
skilllint docs sections <FILE_PATH>
```

**Arguments**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `FILE_PATH` | path | yes | Path to a cached markdown file |

**Output**

- **stdout**: Plain-text table with columns: `index`, `level`, `heading`, `lines`

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | Success |

**Table format**

No Rich terminal markup — plain ASCII table. Each row shows:
- `index`: 0-based section index
- `level`: Heading depth 1–6, or 0 for preamble before first heading
- `heading`: Heading text, or `(preamble)` for content before the first heading
- `lines`: Line span in `start-end` format (1-indexed, inclusive)

### section

Extract and print the full text of a named section from a cached markdown file.

**Synopsis**

```
skilllint docs section <FILE_PATH> <HEADING>
```

**Arguments**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `FILE_PATH` | path | yes | Path to a cached markdown file |
| `HEADING` | string | yes | Heading text or markdown anchor slug to locate (case-insensitive) |

**Heading matching**

Matches both of these formats:
- **Heading text**: `"Hook input and output"` — case-insensitive, leading `#` stripped
- **Markdown anchor slug**: `"hook-input-and-output"` — derived from heading via slug algorithm

**Output**

- **stdout**: Full text of the matching section (including the heading line)
- **stderr**: Error message if not found

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | Section found and printed |
| 1 | Heading not found in the file |

### verify

Verify a cached file against its `.meta.json` sidecar.

**Synopsis**

```
skilllint docs verify <FILE_PATH>
```

**Arguments**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `FILE_PATH` | path | yes | Path to a cached markdown file to verify |

**Output**

- **stdout** (on success): Status, file path, SHA-256 digest, and byte count
- **stderr** (on failure): Detailed comparison of computed vs expected values

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | File is `INTACT` — SHA-256 and byte count match sidecar |
| 1 | File is `MODIFIED` or `UNVERIFIABLE` — sidecar missing or content mismatch |

## CLI: `scripts/fetch_doc_source.py`

Standalone script providing identical functionality to `skilllint docs` via PEP 723 inline metadata. Functions as a single-file utility that can be executed with `uv run --script`.

**Invocation**

```bash
uv run --script scripts/fetch_doc_source.py COMMAND [ARGS] [OPTIONS]
```

**Commands**

Identical to `skilllint docs`:
- `fetch <URL> [--ttl HOURS] [--force]`
- `latest <PAGE_NAME>`
- `sections <FILE_PATH>`
- `section <FILE_PATH> <HEADING>`
- `verify <FILE_PATH>`

**Dependencies** (PEP 723 metadata)

```python
requires-python = ">=3.11"
dependencies = [
  "typer>=0.21.0",
  "httpx>=0.27.0",
  "skilllint",
]

[tool.uv.sources]
skilllint = { path = ".." }
```

The script resolves `skilllint` as a local editable install relative to the parent directory.

**Output behavior**

Identical to `skilllint docs`:
- **stdout**: File paths, section tables, section text
- **stderr**: Status messages, warnings, error panels

## Python API: `skilllint.vendor_cache`

### Enumerations

#### CacheStatus

Result status returned by `fetch_or_cached()`.

| Value | Description |
|-------|-------------|
| `FRESH` | Within TTL; served from on-disk cache without a network request |
| `REFRESHED` | Was stale; re-fetched successfully; content changed on remote |
| `UNCHANGED` | Was stale; re-fetched successfully; content identical to cached copy; sidecar touched with new timestamp |
| `STALE` | Was stale and network unavailable; served from cache anyway |
| `NEW` | First fetch; no prior cache existed |

#### IntegrityStatus

Result status returned by `verify_integrity()`.

| Value | Description |
|-------|-------------|
| `INTACT` | File hash and byte count match sidecar metadata |
| `MODIFIED` | File hash or byte count does not match sidecar metadata |
| `UNVERIFIABLE` | No sidecar found; verification impossible |

### Data Classes

#### CacheResult

Outcome of a `fetch_or_cached()` call.

**Attributes**

| Name | Type | Description |
|------|------|-------------|
| `path` | `Path` | Path to the cached file on disk |
| `status` | `CacheStatus` | How the result was produced (FRESH, REFRESHED, UNCHANGED, STALE, NEW) |
| `page_name` | `str` | Filesystem-safe page name derived from the URL via `derive_page_name()` |
| `url` | `str` | Original URL that was fetched or looked up |

**Usage**

```python
from skilllint.vendor_cache import fetch_or_cached

result = fetch_or_cached("https://docs.anthropic.com/en/docs/claude-code/settings.md")
print(result.path)  # Path object
print(result.status.value)  # "fresh", "new", etc.
```

#### IntegrityResult

Outcome of a `verify_integrity()` call.

**Attributes**

| Name | Type | Description |
|------|------|-------------|
| `status` | `IntegrityStatus` | Whether file is INTACT, MODIFIED, or UNVERIFIABLE |
| `file_path` | `Path` | Path to the file that was checked |
| `computed_sha256` | `str` | SHA-256 hex digest computed from current file content |
| `expected_sha256` | `str \| None` | SHA-256 from sidecar, or None if no sidecar exists |
| `computed_bytes` | `int` | Byte length of current file content (UTF-8 encoded) |
| `expected_bytes` | `int \| None` | Byte length from sidecar, or None if no sidecar exists |

**Usage**

```python
from skilllint.vendor_cache import verify_integrity

result = verify_integrity(Path(".claude/vendor/sources/my-page-2026-03-24-1430.md"))
if result.status.value == "intact":
    print(f"File verified: {result.computed_sha256}")
else:
    print(f"Mismatch: {result.computed_sha256} != {result.expected_sha256}")
```

#### MarkdownSection

A single section within a markdown document.

**Attributes**

| Name | Type | Description |
|------|------|-------------|
| `heading` | `str` | Heading text; empty string for preamble before first heading |
| `level` | `int` | Heading depth 1–6; 0 for the preamble |
| `line_start` | `int` | First line of the section (1-indexed, inclusive) |
| `line_end` | `int` | Last line of the section (1-indexed, inclusive) |

**Usage**

```python
from skilllint.vendor_cache import list_sections

sections = list_sections(Path(".claude/vendor/sources/my-page-2026-03-24-1430.md"))
for sec in sections:
    print(f"{sec.level}: {sec.heading or '(preamble)'} lines {sec.line_start}-{sec.line_end}")
```

### Exceptions

#### NoCacheError

Raised when no cached copy exists and the network is unavailable.

**Inheritance**

Subclass of `Exception`.

**Attributes**

| Name | Type | Description |
|------|------|-------------|
| `url` | `str` | The URL that could not be fetched |
| `reason` | `str` | Human-readable reason for the failure (network error message) |

**Usage**

```python
from skilllint.vendor_cache import fetch_or_cached, NoCacheError

try:
    result = fetch_or_cached("https://example.com/docs.md")
except NoCacheError as exc:
    print(f"Failed to fetch {exc.url}: {exc.reason}")
```

### Functions

#### derive_page_name

Extract a filesystem-safe page name from a documentation URL.

**Signature**

```python
def derive_page_name(url: str) -> str:
```

**Algorithm**

1. Parse the URL and extract the path component
2. Strip common prefixes one at a time until none remain: `/en/`, `/docs/`, `/api/`
3. Strip `.md` extension if present
4. Split the path on `/` and discard empty segments
5. Join remaining segments with `--`
6. Replace any non-alphanumeric-or-hyphen character with a hyphen
7. Collapse multiple consecutive hyphens to double hyphens

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `url` | `str` | Full documentation URL |

**Returns**

`str` — Filesystem-safe page name suitable for use as a filename prefix

**Raises**

None — always succeeds (URL parsing is lenient)

**Examples**

| Input | Output |
|-------|--------|
| `https://docs.anthropic.com/en/docs/claude-code/settings.md` | `claude-code--settings` |
| `https://cursor.com/docs/context/rules.md` | `context--rules` |
| `https://code.claude.com/docs/en/sub-agents.md` | `sub-agents` |

#### find_latest

Find the most recent cached file for a given page name.

**Signature**

```python
def find_latest(page_name: str, *, sources_dir: Path | None = None) -> Path | None:
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `page_name` | `str` | — | Filesystem-safe page name (output of `derive_page_name()`) |
| `sources_dir` | `Path \| None` | `None` (uses `SOURCES_DIR`) | Directory to search for cached files |

**Returns**

`Path | None` — Path to the latest cached file matching `{page_name}-*.md`, or `None` if no matches exist

**Behavior**

Scans *sources_dir* for all files matching the glob pattern `{page_name}-*.md` (excluding `.meta.json` files). Returns the path whose filename sorts lexicographically last. Timestamps in `YYYY-MM-DD-HHMM` format sort correctly by lexicographic order, so the most recent file is returned.

**Examples**

```python
from skilllint.vendor_cache import find_latest
from pathlib import Path

path = find_latest("claude-code--settings")
if path:
    print(f"Found: {path}")  # .claude/vendor/sources/claude-code--settings-2026-03-24-1430.md
```

#### fetch_or_cached

Fetch a documentation page, or return a cached copy. Implements offline-first behavior with TTL-based freshness and network error recovery.

**Signature**

```python
def fetch_or_cached(url: str, *, ttl_hours: float = 4.0, force: bool = False) -> CacheResult:
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | `str` | — | URL of the documentation page to fetch |
| `ttl_hours` | `float` | 4.0 | Maximum age in hours before a cached copy is considered stale |
| `force` | `bool` | False | If True, skip freshness check and always attempt network fetch |

**Returns**

`CacheResult` — Describes the outcome, including path, status, page_name, and original URL

**Raises**

`NoCacheError` — If no cached copy exists and the network is unavailable

**Flow**

1. **Derive page name**: Extract filesystem-safe name from URL via `derive_page_name()`
2. **Look up cache**: Find the latest cached file for the page_name via `find_latest()`

3. **If cached file exists and force=False**:
   - Load its `.meta.json` sidecar and check age against `ttl_hours`
   - **Fresh (age < TTL)**: Return status=`FRESH`, path=cached file
   - **Stale (age >= TTL)**: Attempt network fetch
     - Network OK, content changed: Write new timestamped file, return status=`REFRESHED`
     - Network OK, content identical: Update `fetched_at` in sidecar only, return status=`UNCHANGED`
     - Network failure (ConnectError, TimeoutException, HTTPError): Serve stale copy, return status=`STALE`

4. **If no cached file or force=True**:
   - Attempt network fetch
   - Network OK: Write new timestamped file, return status=`NEW`
   - Network failure: Raise `NoCacheError`

**File naming**

New cached files are written as: `{SOURCES_DIR}/{page_name}-{YYYY-MM-DD-HHMM}.md`

The timestamp is in UTC and uses 24-hour format with no seconds.

**Examples**

```python
from skilllint.vendor_cache import fetch_or_cached, CacheStatus

# Fresh cache available
result = fetch_or_cached("https://docs.anthropic.com/en/docs/claude-code/settings.md")
print(result.status)  # CacheStatus.FRESH

# Force refresh
result = fetch_or_cached("https://docs.anthropic.com/en/docs/claude-code/settings.md", force=True)
print(result.status)  # CacheStatus.REFRESHED or CacheStatus.UNCHANGED

# Custom TTL (30 minutes)
result = fetch_or_cached("https://example.com/api.md", ttl_hours=0.5)
```

#### list_sections

Parse a markdown file into a list of `MarkdownSection` objects.

**Signature**

```python
def list_sections(file_path: Path) -> list[MarkdownSection]:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `file_path` | `Path` | Path to the markdown file to parse |

**Returns**

`list[MarkdownSection]` — Sections in document order, including preamble if present

**Parsing rules**

- Uses marko (AST-based markdown parser) to correctly identify ATX headings while ignoring `#` lines inside fenced code blocks
- Content before the first heading becomes a preamble section with `heading=""` and `level=0`
- Each section spans from its heading line to the line immediately before the next heading of equal or higher level (lower number), or EOF
- Lines are 1-indexed to match the Read tool's display format

**Examples**

```python
from skilllint.vendor_cache import list_sections
from pathlib import Path

sections = list_sections(Path(".claude/vendor/sources/my-page-2026-03-24-1430.md"))
for sec in sections:
    print(f"Level {sec.level}: {sec.heading!r} (lines {sec.line_start}–{sec.line_end})")
```

#### read_section

Return the full text of the section matching a heading.

**Signature**

```python
def read_section(file_path: Path, heading: str) -> str | None:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `file_path` | `Path` | Path to the markdown file |
| `heading` | `str` | Heading text or markdown anchor slug to find |

**Returns**

`str | None` — Full text of the matching section (including the heading line), or `None` if no match is found

**Heading matching**

Supports two formats:
- **Heading text** (case-insensitive): `"Hook input and output"`
- **Markdown anchor slug**: `"hook-input-and-output"` (derived via slug algorithm)

Leading `#` characters and surrounding whitespace are stripped before comparison. Both heading text and slug are tested against the query.

**Examples**

```python
from skilllint.vendor_cache import read_section
from pathlib import Path

path = Path(".claude/vendor/sources/my-page-2026-03-24-1430.md")

# By heading text
text = read_section(path, "Hook input and output")

# By slug
text = read_section(path, "hook-input-and-output")

# Case-insensitive
text = read_section(path, "HOOK INPUT AND OUTPUT")
```

#### format_section_index

Return a plain-text table of sections in a markdown file.

**Signature**

```python
def format_section_index(file_path: Path) -> str:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `file_path` | `Path` | Path to the markdown file |

**Returns**

`str` — Multi-line plain-text table suitable for printing to stdout

**Table format**

Columns (in order):
- `index` (0-indexed section number)
- `level` (heading depth 1–6, or 0 for preamble)
- `heading` (heading text, or `(preamble)` if empty)
- `lines` (line span in `start-end` format, 1-indexed, inclusive)

No Rich terminal markup — pure ASCII. Column widths auto-fit content.

**Examples**

```python
from skilllint.vendor_cache import format_section_index
from pathlib import Path

table = format_section_index(Path(".claude/vendor/sources/my-page-2026-03-24-1430.md"))
print(table)
# Output:
# index  level  heading                 lines
# -----  -----  ----------------------  --------
# 0      0      (preamble)              1-5
# 1      1      Getting Started         6-20
# 2      2      Installation            21-35
# 3      2      Configuration           36-50
```

#### verify_integrity

Verify a cached file against its `.meta.json` sidecar.

**Signature**

```python
def verify_integrity(file_path: Path) -> IntegrityResult:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `file_path` | `Path` | Path to the cached markdown file to verify |

**Returns**

`IntegrityResult` — Describes the verification outcome

**Verification logic**

1. Read the file and compute its SHA-256 hex digest and byte count
2. Load the `.meta.json` sidecar (if it exists)
3. Compare computed values against sidecar values:
   - Both hash and byte count match: status=`INTACT`
   - Hash or byte count mismatch: status=`MODIFIED`
   - No sidecar exists: status=`UNVERIFIABLE`

The IntegrityResult always includes both computed and expected values, allowing callers to display a detailed comparison.

**Examples**

```python
from skilllint.vendor_cache import verify_integrity, IntegrityStatus
from pathlib import Path

result = verify_integrity(Path(".claude/vendor/sources/my-page-2026-03-24-1430.md"))

if result.status == IntegrityStatus.INTACT:
    print(f"File is intact: {result.computed_sha256}")
else:
    print(f"Mismatch detected:")
    print(f"  Computed: {result.computed_sha256} ({result.computed_bytes} bytes)")
    print(f"  Expected: {result.expected_sha256} ({result.expected_bytes} bytes)")
```

## Python API: `skilllint.vendor_io`

Low-level I/O utilities imported by vendor cache functions and scripts.

### Constants

#### PROJECT_ROOT

Absolute path to the repository root.

**Type**: `Path`

**Derivation**: `vendor_io.py` is located at `packages/skilllint/vendor_io.py`. Its parent chain: `.parent` → `packages/skilllint/`, `.parent.parent` → `packages/`, `.parent.parent.parent` → repo root (contains `pyproject.toml`).

**Usage**

```python
from skilllint.vendor_io import PROJECT_ROOT
print(PROJECT_ROOT)  # /path/to/agentskills-linter
```

#### VENDOR_DIR

Vendor documentation directory inside `.claude/`.

**Type**: `Path`

**Value**: `{PROJECT_ROOT} / ".claude" / "vendor"`

**Usage**

```python
from skilllint.vendor_io import VENDOR_DIR
print(VENDOR_DIR)  # /path/to/agentskills-linter/.claude/vendor
```

#### SOURCES_DIR

Per-source cached documents directory.

**Type**: `Path`

**Value**: `{VENDOR_DIR} / "sources"`

**Usage**

```python
from skilllint.vendor_io import SOURCES_DIR
print(SOURCES_DIR)  # /path/to/agentskills-linter/.claude/vendor/sources
```

### Functions

#### sha256_hex

Return full hex SHA-256 digest of text content.

**Signature**

```python
def sha256_hex(text: str) -> str:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `text` | `str` | String content to hash (encoded as UTF-8) |

**Returns**

`str` — 64-character hex-encoded SHA-256 digest

#### sha256_hex_short

Return truncated hex SHA-256 digest.

**Signature**

```python
def sha256_hex_short(text: str, *, length: int = 12) -> str:
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | `str` | — | String content to hash (encoded as UTF-8) |
| `length` | `int` | 12 | Number of hex characters to return |

**Returns**

`str` — Hex-encoded SHA-256 digest truncated to `length` characters

#### read_text_or_none

Read file content as UTF-8, or return None if missing.

**Signature**

```python
def read_text_or_none(path: Path) -> str | None:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `path` | `Path` | Path to the file to read |

**Returns**

`str | None` — File content as a string, or `None` if the file does not exist

**Exceptions**

None — returns `None` instead of raising `FileNotFoundError`

#### write_json

Write JSON with indent=2 and a trailing newline.

**Signature**

```python
def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `path` | `Path` | Destination file path |
| `data` | `dict[str, Any] \| list[Any]` | JSON-serializable dict or list to write |

**Behavior**

- Creates parent directories if they do not exist
- Writes with `indent=2` for human readability
- Appends trailing newline (POSIX text file convention)

#### load_json_or_none

Load JSON from path, or return None if missing or unparseable.

**Signature**

```python
def load_json_or_none(path: Path) -> dict[str, Any] | None:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `path` | `Path` | Path to the JSON file |

**Returns**

`dict[str, Any] | None` — Parsed dict, or `None` if the file does not exist or contains invalid JSON

**Exceptions**

None — returns `None` on FileNotFoundError, JSONDecodeError, or OSError

#### fetch_url_text

Fetch a URL and return the response body as text.

**Signature**

```python
def fetch_url_text(url: str, *, timeout: float = 30.0, follow_redirects: bool = True) -> str:
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | `str` | — | The URL to fetch |
| `timeout` | `float` | 30.0 | Request timeout in seconds |
| `follow_redirects` | `bool` | True | Whether to follow HTTP redirects |

**Returns**

`str` — Response body decoded as text

**Raises**

- `httpx.HTTPStatusError` — On non-2xx HTTP responses
- `ValueError` — If the response body is empty
- `httpx.ConnectError` — Network connection failure
- `httpx.TimeoutException` — Request timeout exceeded

**HTTP client**

Uses `httpx.Client` with the specified timeout and redirect behavior. Automatically raises on non-2xx status via `response.raise_for_status()`.

#### write_sidecar

Write a `.meta.json` sidecar alongside a saved file.

**Signature**

```python
def write_sidecar(md_path: Path, *, url: str, content: str) -> Path:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `md_path` | `Path` | Path to the saved content file (typically a `.md` file) |
| `url` | `str` | The URL the content was fetched from |
| `content` | `str` | The raw text content that was saved |

**Returns**

`Path` — Path to the written sidecar file

**Sidecar content**

Records provenance metadata:
- `url` — Source URL
- `fetched_at` — ISO 8601 UTC timestamp
- `sha256` — Hex SHA-256 digest of the content
- `byte_count` — Byte length of UTF-8 encoded content

**Sidecar path convention**

For file `/path/to/file.md`, the sidecar is `/path/to/file.meta.json` (same name, `.meta.json` suffix).

#### load_sidecar

Load the `.meta.json` sidecar for a given file path.

**Signature**

```python
def load_sidecar(md_path: Path) -> dict[str, Any] | None:
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `md_path` | `Path` | Path to the content file whose sidecar to load |

**Returns**

`dict[str, Any] | None` — Parsed sidecar dict, or `None` if the sidecar is missing or corrupt

#### utc_now_iso

Return current UTC time as an ISO 8601 string.

**Signature**

```python
def utc_now_iso() -> str:
```

**Returns**

`str` — UTC timestamp in ISO 8601 format, e.g. `"2026-03-23T14:05:00+00:00"`

## File Format: `.meta.json` Sidecar

Provenance and integrity metadata for cached documentation files. Written alongside each `.md` file with the same basename.

**Path convention**

```
{SOURCES_DIR}/{page_name}-{YYYY-MM-DD-HHMM}.md
{SOURCES_DIR}/{page_name}-{YYYY-MM-DD-HHMM}.meta.json
```

**Schema**

```json
{
  "url": "string",
  "fetched_at": "string",
  "sha256": "string",
  "byte_count": "integer"
}
```

**Field descriptions**

| Field | Type | Description |
|-------|------|-------------|
| `url` | `string` | Source URL the content was fetched from |
| `fetched_at` | `string` | ISO 8601 UTC timestamp when the file was fetched (e.g. `"2026-03-23T14:05:00+00:00"`) |
| `sha256` | `string` | Hex-encoded SHA-256 digest of the file content (64 characters) |
| `byte_count` | `integer` | Byte length of the UTF-8 encoded content |

**Example**

```json
{
  "url": "https://docs.anthropic.com/en/docs/claude-code/settings.md",
  "fetched_at": "2026-03-23T14:05:00+00:00",
  "sha256": "a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789",
  "byte_count": 12345
}
```

## File Naming Convention

Cached documentation files use a standardized naming pattern that sorts correctly by timestamp and remains human-readable.

**Format**

```
{page_name}-{YYYY-MM-DD-HHMM}.md
```

**Components**

| Component | Example | Description |
|-----------|---------|-------------|
| `page_name` | `claude-code--settings` | Filesystem-safe name derived from URL via `derive_page_name()` |
| `YYYY-MM-DD` | `2026-03-23` | Date in ISO 8601 format |
| `HHMM` | `1405` | Time in 24-hour format (hours + minutes, UTC) |

**Lexicographic sort property**

Timestamps in `YYYY-MM-DD-HHMM` format sort correctly by lexicographic (alphabetic) order. The most recent file for a given `page_name` is always the one with the filename that sorts last:

```
claude-code--settings-2026-03-22-1000.md
claude-code--settings-2026-03-23-1405.md  ← Latest
claude-code--settings-2026-03-24-0930.md
```

**Examples**

| URL | page_name | Filename |
|-----|-----------|----------|
| `https://docs.anthropic.com/en/docs/claude-code/settings.md` | `claude-code--settings` | `claude-code--settings-2026-03-24-1430.md` |
| `https://cursor.com/docs/context/rules.md` | `context--rules` | `context--rules-2026-03-24-1430.md` |
| `https://code.claude.com/docs/en/sub-agents.md` | `sub-agents` | `sub-agents-2026-03-24-1430.md` |

## Configuration

The vendor cache system has no configuration file. All settings are function parameters or CLI options.

**TTL (Time-To-Live)**

Default: 4.0 hours

Configurable via:
- CLI: `--ttl` option on `skilllint docs fetch` and `scripts/fetch_doc_source.py fetch`
- Python API: `ttl_hours` parameter on `fetch_or_cached()`

A file is considered stale when its age (time since `fetched_at` in the sidecar) exceeds the TTL. Stale files trigger a network refresh attempt; if the network is unavailable, the stale copy is served.

**SOURCES_DIR**

Default: `{PROJECT_ROOT} / ".claude" / "vendor" / "sources"`

The constant is defined in `skilllint.vendor_io.SOURCES_DIR` and cannot be reconfigured via environment variables or config files. To use a different directory, pass `sources_dir` to `find_latest()` or create cached files manually in the desired location.

**Force flag**

Available via:
- CLI: `--force` option on `skilllint docs fetch` and `scripts/fetch_doc_source.py fetch`
- Python API: `force` parameter on `fetch_or_cached()`

When `force=True`, the freshness check is skipped and a network fetch is always attempted. If the network is unavailable, the stale copy (if one exists) is served anyway.

**No TTL on UNCHANGED status**

When `fetch_or_cached()` detects that remote content is identical to the cached copy, it updates only the `fetched_at` timestamp in the sidecar (status=`UNCHANGED`). The existing `.md` file is not rewritten. This optimizes for network efficiency: the metadata is fresh (TTL resets) without rewriting unchanged content.
