# AGENTS.md

## Running skilllint during development

Always invoke the CLI via `uv run skilllint …` — it resolves to the editable
source in `.venv` (current worktree HEAD). Never `uv tool install`; a frozen
global copy goes stale and shadows the source you're editing.
