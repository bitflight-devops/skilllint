# Vendor documentation cache

`skilllint docs` stores on-demand vendor pages under the project vendor cache
and prints the selected path. The cache stores decoded response text encoded as
UTF-8, with a JSON sidecar containing provenance, SHA-256, and byte count. The
Markdown file and sidecar are separate writes; missing or partial pairs are
detectable with `verify`, not atomic transactions.

## Choose the source first

Before capturing a URL, inspect `.claude/vendor/{provider}/` for an equivalent
authoritative Markdown or RST file from the maintained vendor clone. Record the
path and heading/section read. This local-source branch makes no URL request.
When no equivalent source exists, capture the page and read the path printed by
the existing command:

```bash
CACHE_PATH="$(uv run skilllint docs fetch "https://example.com/guide.md")"
uv run skilllint docs sections "$CACHE_PATH"
```

The rendered page remains authoritative when its content cannot be represented
by the clone's Markdown/RST. In that case URL capture is allowed. The
`fetch-authorities` command is likewise an on-demand URL operation, after the
same local-source check; it does not select clone content automatically.

## Lifecycle recipe

The following commands use a shell-captured path, so they do not depend on a
timestamp or home directory. Status is written to stderr; the path and query
content are written to stdout.

```bash
# First successful capture: NEW
CACHE_PATH="$(uv run skilllint docs fetch "https://example.com/guide.md")"

# Existing file within the TTL: FRESH (no request)
uv run skilllint docs fetch "https://example.com/guide.md"

# Force a request. Identical text is UNCHANGED; changed text is REFRESHED.
uv run skilllint docs fetch "https://example.com/guide.md" --force

# TTL is in hours. TTL 0 means attempt refresh on every call; successful text
# is still cached. A failed refresh with a cache returns STALE.
uv run skilllint docs fetch "https://example.com/guide.md" --ttl 0
```

`NEW` means no previous cache existed. `FRESH` serves the existing pair without
network access. `UNCHANGED` keeps the existing path and repairs/touches its
sidecar when fetched text is identical. `REFRESHED` writes a new cached version
when text differs and retains the old version. `STALE` serves an existing pair
when refresh fails. With no pair, a failed request exits 1 with `No Cache
Available` and prints no path.

## Query and verify

```bash
LATEST_PATH="$(uv run skilllint docs latest "$(python -c 'from skilllint.vendor_io import derive_page_name; print(derive_page_name("https://example.com/guide.md"))')")"
uv run skilllint docs sections "$LATEST_PATH"
uv run skilllint docs section "$LATEST_PATH" "Usage"
uv run skilllint docs verify "$LATEST_PATH"
```

`sections` reports real Markdown headings and ignores headings inside fenced
code. `section` accepts heading text or its lowercase Markdown slug. `verify`
returns `INTACT` (exit 0) when the file matches its sidecar; modified,
missing, malformed, or incomplete metadata returns `MODIFIED` or
`UNVERIFIABLE` (exit 1). An empty successful HTTP response is an unsuccessful
fetch: with a cache it follows stale fallback, and without one it is a bounded
failure rather than a false successful path.
To fetch every normalized rule authority URL after performing the source-first
check for each provider:

```bash
uv run skilllint docs fetch-authorities
```

## Roots and retained history

Source checkouts and linked worktrees share the project vendor root; tracked
schema outputs remain worktree-local. Installed wheel and `uvx` invocations
resolve their runtime cache owner from the invocation project/root contract,
while a non-Git working directory falls back to that working directory. The
standalone script is source-coupled to this checkout and uses the same cache
implementation:

```bash
uv run --script scripts/fetch_doc_source.py fetch "https://example.com/guide.md"
uv run --script scripts/fetch_doc_source.py latest "example--guide"
uv run --script scripts/fetch_doc_source.py sections "$LATEST_PATH"
uv run --script scripts/fetch_doc_source.py section "$LATEST_PATH" "Usage"
uv run --script scripts/fetch_doc_source.py verify "$LATEST_PATH"
```

Do not infer source selection from a cache status: `FRESH` and `STALE` describe
the cache response only, not whether a local clone was consulted. The older
cache guides retired in Todo 23 are not part of the maintained documentation
surface.
