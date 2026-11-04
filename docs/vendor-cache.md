# Vendor documentation cache

Use `skilllint docs` to save vendor documentation, read individual sections, and check whether a cached copy has changed. A cached page remains available when a refresh cannot reach the source.

The examples use an installed `skilllint` command. In a skilllint source checkout, use `uv run skilllint` instead. See [installation](usage.md#install) if the command is unavailable.

## Choose the source first

When researching rules in this repository, inspect `.claude/vendor/{provider}/` for an equivalent authoritative Markdown or RST file from the maintained vendor clone. Read that file and record its path and heading or section. This makes no URL request.

Capture the URL when no equivalent local source exists, or when the rendered page contains authoritative information that the clone's Markdown or RST cannot represent. The cache command does not select clone content automatically.

## Fetch and read a page

Replace the example URL below with the documentation page you need. Prefer a Markdown source URL when you want to query headings. `fetch` saves the response text; it does not convert an HTML page to Markdown.

```bash
URL="https://example.com/guide.md"
CACHE_PATH="$(skilllint docs fetch "$URL")"
skilllint docs sections "$CACHE_PATH"
skilllint docs section "$CACHE_PATH" "Usage"
skilllint docs verify "$CACHE_PATH"
```

Use a heading listed by `sections` in place of `Usage`. `section` accepts heading text or its lowercase Markdown slug. Headings inside fenced code blocks are ignored.

`fetch` prints the selected file path to stdout and status information to stderr. Capture its path rather than constructing a filename from a timestamp. If the fetch fails without a cached copy, it exits `1`, reports `No Cache Available`, and prints no path. Check that the fetch succeeded before using its result.

`verify` returns `INTACT` with exit status `0` when the cached file matches its metadata. Changed content produces `MODIFIED`; missing, malformed, or incomplete metadata produces `UNVERIFIABLE`. Both exit `1`. The cache stores decoded response text encoded as UTF-8, with a separate `.meta.json` sidecar recording its source URL, SHA-256, and byte count. The two files are written separately, so use `verify` to detect missing or partial pairs.

## Refresh a cached page

The default time-to-live is four hours. Within that interval, `fetch` returns the cached path without making a request. Use `--force` to refresh immediately, or `--ttl` to set the freshness interval in hours:

```bash
skilllint docs fetch "$URL"
skilllint docs fetch "$URL" --force
skilllint docs fetch "$URL" --ttl 0
```

`--ttl 0` attempts a refresh on every call and still saves successful responses. Fetch statuses describe what happened:

- `NEW`: no previous cached file existed; the page was fetched and saved.
- `FRESH`: the cached file is within the freshness interval; no request was made.
- `UNCHANGED`: the fetched text matches the cached file; its metadata was refreshed or repaired.
- `REFRESHED`: the fetched text differs; the new content was saved.
- `STALE`: the refresh failed; the existing cached file was returned.

An empty successful HTTP response is treated as a failed fetch: an existing copy is returned as `STALE`, or the command fails if none exists. `FRESH` and `STALE` describe cache age and retrieval, not source selection or integrity. Use `verify` when you need to check the stored file.

## Find a previously cached page

`latest` takes a page name, not a URL. For the example URL `https://example.com/guide.md`, the name is `guide`:

```bash
LATEST_PATH="$(skilllint docs latest guide)"
skilllint docs sections "$LATEST_PATH"
```

Page names come from the URL path: common leading `en`, `docs`, and `api` segments and a final `.md` are removed, and remaining path segments are joined with `--`. For example, `/en/docs/claude-code/settings.md` becomes `claude-code--settings`. `latest` exits `1` when no matching cached file exists.

## Fetch rule authority pages

The `fetch-authorities` command is likewise an on-demand URL operation. After checking each provider's local sources as described above, use it to fetch every unique normalized authority URL in the rule registry:

```bash
skilllint docs fetch-authorities
```

The command prints one cached path per successful URL. It continues after a failed fetch and exits `1` if any URL has neither a successful response nor an available cached copy.

## Cache location

Pages are saved under `.claude/vendor/sources/` as `{page-name}-{YYYY-MM-DD-HHMM}.md`, alongside their metadata files.

- A skilllint source checkout uses its own vendor directory. Linked worktrees share the primary checkout's vendor directory.
- An installed wheel or `uvx` invocation uses the enclosing Git repository. Linked worktrees again share the primary checkout's directory.
- Outside a Git repository, an installed invocation uses the current working directory.

## Run from a source checkout

The standalone script uses the same cache implementation and is available before the CLI is installed. Run it from this repository's root:

```bash
uv run --script scripts/fetch_doc_source.py fetch "$URL"
LATEST_PATH="$(uv run --script scripts/fetch_doc_source.py latest guide)"
uv run --script scripts/fetch_doc_source.py sections "$LATEST_PATH"
uv run --script scripts/fetch_doc_source.py section "$LATEST_PATH" "Usage"
uv run --script scripts/fetch_doc_source.py verify "$LATEST_PATH"
```

Replace `guide` and `Usage` with the page name and heading for your URL. For automated consumers, the CLI commands also accept `--json`; see the [output reference](output-formats.md).
