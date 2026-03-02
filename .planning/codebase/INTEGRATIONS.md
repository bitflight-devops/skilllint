# External Integrations

**Analysis Date:** 2026-03-02

## APIs & External Services

**Documentation References (read-only):**
- Claude Code Plugin Reference: https://code.claude.com/docs/en/plugins-reference.md#plugin-manifest-schema
- Claude Code Skills Reference: https://code.claude.com/docs/en/skills.md#frontmatter-reference
- Error codes reference: https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md
  - No SDK client — these are documentation links only

**External Namespace References (validated but not called):**
- Live API integration: Validation checks for references like "live-api-integration-tester"
- GitHub project manager: Validation checks for references like "github-project-manager"
- HTTP/HTTPS URLs: Recognized and stripped during namespace validation but not dereferenced

## Data Storage

**Databases:**
- Not applicable - skilllint is a static analysis tool

**File Storage:**
- Local filesystem only - reads plugin.json, SKILL.md, agents/*.md, commands/*.md files
- Manifest files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Temporary files: Uses Python tempfile module for snapshot operations

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None - skilllint is a local static analysis tool with no authentication

**Git Identity:**
- Uses git config for repository metadata (git.Repo operations)
- Reads remote URL via GitPython (PR004 validation checks repository URL against git remote)
- No SSH keys or credentials required beyond git system configuration

## Monitoring & Observability

**Error Tracking:**
- None - no external error tracking

**Logs:**
- Console output via Rich library
- ANSI color codes stripped in CI environments (detected via FORCE_COLOR)
- Structured error reporting via ValidationError messages
- No persistent logging to files or external systems

## CI/CD & Deployment

**Hosting:**
- Not applicable - distributed as Python package/scripts via pip or uv

**CI Pipeline:**
- No CI pipeline integration detected at package level
- Expected use: Pre-commit hook or CI validation step

**Git Integration:**
- Pre-commit hook: `auto_sync_manifests.py` mode to detect staged file changes
- Git operations: `git diff --cached --name-status` for staged changes
- Git metadata: `git show HEAD:filepath` to read previous file state for comparison
- Git staging: `git add` to stage updated manifest files
- Windows support: Resolves git-bash path via `shutil.which("git-bash")` or LOCALAPPDATA registry

## Environment Configuration

**Required env vars:**
- None are strictly required for basic operation

**Optional env vars:**
- `CLAUDECODE` - Set to detect Claude Code environment (affects console output)
- `CLAUDE_CODE_REMOTE` - Set to "true" to enable remote mode detection
- `NO_COLOR` - Set to disable Rich terminal colors (standard convention)
- `LOCALAPPDATA` - Windows-only, read to find git-bash installation

**Secrets location:**
- Not applicable - skilllint is read-only analysis, requires no secrets or credentials

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Pre-commit Integration

**Hook Type:**
- Can be used as pre-commit hook to validate and auto-fix skills/agents/commands on commit
- `auto_sync_manifests.py` in pre-commit mode (default) detects CRUD operations on git staged files
- `plugin_validator.py` can be invoked via pre-commit to validate before commit

---

*Integration audit: 2026-03-02*
