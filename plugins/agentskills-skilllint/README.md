# agentskills-skilllint

Use skilllint from Claude Code to check agent skills, plugins, agents, commands, and platform files. The plugin helps Claude explain findings, apply supported fixes, and check the result.

## Load the plugin

From the root of a checkout of this repository, start a Claude Code session with the plugin:

```bash
claude --plugin-dir ./plugins/agentskills-skilllint
```

The plugin needs the skilllint CLI. Use an existing installation, or choose one of these options:

```bash
uvx skilllint@latest --version     # Run with uv, without a permanent installation
pipx run skilllint --version       # Run with pipx, without a permanent installation
python -m pip install skilllint    # Install with pip, then use skilllint
```

The skill uses the same invocation form for subsequent commands. If you are developing skilllint itself, follow the [repository development instructions](../../AGENTS.md) and use the checkout's CLI.

This repository does not include a marketplace entry. The `--plugin-dir` command loads the plugin for that session; for persistent distribution, use your organization's supported Claude plugin installation process.

## Use the skill

Claude Code exposes the plugin skill as `/agentskills-skilllint:skilllint`, using the [plugin name as its namespace](https://code.claude.com/docs/en/plugins/components#explore-the-plugin-directory).

Check the current repository scope:

```text
/agentskills-skilllint:skilllint
```

Explain a finding:

```text
/agentskills-skilllint:skilllint FM004
```

Check a specific path:

```text
/agentskills-skilllint:skilllint ./plugins/my-plugin
```

You can also ask Claude to lint a path or investigate a skilllint finding in natural language. Name the target platform when you want the scan limited to that platform.

The skill reads rule IDs from the scan and queries `skilllint rule <ID>` for their meaning and remediation. When fixing findings, it uses the installed CLI's current fix support, reviews the edits, and runs validation again.

## Find rule and command details

Query the installed CLI for the current rule catalog, severities, platform scope, and available options:

```bash
skilllint --help
skilllint check --help
skilllint rules
skilllint rule <ID>
```

See the [usage guide](../../docs/usage.md) for configuration and CI integration. The [skill instructions](skills/skilllint/SKILL.md) describe the agent workflow.

## License

MIT
