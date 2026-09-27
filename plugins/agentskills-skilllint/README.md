# agentskills-skilllint

A Claude Code plugin that teaches agents a stable procedure for using the
`skilllint` CLI without duplicating the CLI's changing rule catalog or
configuration metadata.

## What it does

The `/skilllint` skill directs an agent to:

- locate or invoke the current `skilllint` executable;
- scan the requested path with `skilllint check`;
- use emitted rule IDs rather than guessing which rule applies;
- query `skilllint rule <ID>` for current explanation and remediation;
- query `skilllint rules` for current catalog metadata;
- apply `--fix` only through a currently supported CLI route;
- re-run validation after edits.

Rule IDs, severities, fixability, thresholds, and command inventory remain
owned by the installed `skilllint` runtime rather than this plugin.

## Installation

Load this repository plugin for a session:

```bash
claude --plugin-dir ./plugins/agentskills-skilllint
```

This repository does not publish a persistent marketplace entry. Copy or
package the plugin through your organization's supported Claude distribution
process when persistent installation is required.

## Usage

Invoke the full workflow:

```text
/skilllint
```

Explain a finding using the current runtime:

```text
/skilllint FM004
```

Validate a path:

```text
/skilllint ./plugins/my-plugin
```

The skill may also be selected automatically for requests to lint or validate
agent plugins, skills, agents, commands, and related platform files.

## Runtime reference

Use the CLI rather than this README for changing product facts:

```bash
skilllint --help
skilllint rules
skilllint rule <ID>
skilllint check --help
```

If `skilllint` is not installed and `uvx` is available:

```bash
uvx skilllint@latest --version
```

## License

MIT
