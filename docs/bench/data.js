window.BENCHMARK_DATA = {
  "lastUpdate": 1791668083876,
  "repoUrl": "https://github.com/bitflight-devops/skilllint",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "1d395b28fd5724b53c430aab60a54ca495cd0dce",
          "message": "fix(bench): make the clean benchmark fixture actually clean (#328)\n\nbenchmark-plugin-1000-skills.zip is documented as \"clean, no violations\"\nand timed as the scan-clean scenario, but every one of its 1000 files\nreported FM010, SK008, SK005, SK006 and 28 LK001 findings. No generator\nexisted for it; the same findings appear when the rules at the commit\nthat added it (bcdfd32) scan it, so this is not rule drift.\n\nAdd scripts/generate_clean_fixture.py (deterministic, mirrors\ngenerate_violations_fixture.py), regenerate the archive with it, and add\ntests/test_benchmark_clean_fixture.py, which runs the real CLI on the\nextracted archive and asserts exit 0 and no rule findings.\n\n\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-10-06T14:27:22Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/1d395b28fd5724b53c430aab60a54ca495cd0dce"
        },
        "date": 1791296992646,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 2610.295,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 2835.338,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 3246.795,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 353.044,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "dependabot[bot]",
            "username": "dependabot[bot]",
            "email": "49699333+dependabot[bot]@users.noreply.github.com"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "a08c63f2cec8ed1c7f999ba294e0b8d607c6598d",
          "message": "build(deps-dev): bump the python-dev group across 1 directory with 6 updates (#323)\n\n* build(deps-dev): bump the python-dev group across 1 directory with 6 updates\n\nBumps the python-dev group with 6 updates in the / directory:\n\n| Package | From | To |\n| --- | --- | --- |\n| [hatchling](https://github.com/pypa/hatch) | `1.32.3` | `1.32.4` |\n| [hypothesis](https://github.com/HypothesisWorks/hypothesis) | `6.168.0` | `6.168.3` |\n| [prek](https://github.com/j178/prek) | `0.5.3` | `0.5.4` |\n| [pytest-mock](https://github.com/pytest-dev/pytest-mock) | `3.15.1` | `3.16.0` |\n| [ruff](https://github.com/astral-sh/ruff) | `0.16.8` | `0.16.10` |\n| [ty](https://github.com/astral-sh/ty) | `0.0.82` | `0.0.84` |\n\n\n\nUpdates `hatchling` from 1.32.3 to 1.32.4\n- [Release notes](https://github.com/pypa/hatch/releases)\n- [Commits](https://github.com/pypa/hatch/compare/hatchling-v1.32.3...hatchling-v1.32.4)\n\nUpdates `hypothesis` from 6.168.0 to 6.168.3\n- [Release notes](https://github.com/HypothesisWorks/hypothesis/releases)\n- [Commits](https://github.com/HypothesisWorks/hypothesis/compare/v6.168.0...v6.168.3)\n\nUpdates `prek` from 0.5.3 to 0.5.4\n- [Release notes](https://github.com/j178/prek/releases)\n- [Changelog](https://github.com/j178/prek/blob/master/CHANGELOG.md)\n- [Commits](https://github.com/j178/prek/compare/v0.5.3...v0.5.4)\n\nUpdates `pytest-mock` from 3.15.1 to 3.16.0\n- [Release notes](https://github.com/pytest-dev/pytest-mock/releases)\n- [Changelog](https://github.com/pytest-dev/pytest-mock/blob/main/CHANGELOG.rst)\n- [Commits](https://github.com/pytest-dev/pytest-mock/compare/v3.15.1...v3.16.0)\n\nUpdates `ruff` from 0.16.8 to 0.16.10\n- [Release notes](https://github.com/astral-sh/ruff/releases)\n- [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md)\n- [Commits](https://github.com/astral-sh/ruff/compare/0.16.8...0.16.10)\n\nUpdates `ty` from 0.0.82 to 0.0.84\n- [Release notes](https://github.com/astral-sh/ty/releases)\n- [Changelog](https://github.com/astral-sh/ty/blob/main/CHANGELOG.md)\n- [Commits](https://github.com/astral-sh/ty/compare/0.0.82...0.0.84)\n\n---\nupdated-dependencies:\n- dependency-name: hatchling\n  dependency-version: 1.32.4\n  dependency-type: direct:development\n  update-type: version-update:semver-patch\n  dependency-group: python-dev\n- dependency-name: hypothesis\n  dependency-version: 6.168.3\n  dependency-type: direct:development\n  update-type: version-update:semver-patch\n  dependency-group: python-dev\n- dependency-name: prek\n  dependency-version: 0.5.4\n  dependency-type: direct:development\n  update-type: version-update:semver-patch\n  dependency-group: python-dev\n- dependency-name: pytest-mock\n  dependency-version: 3.16.0\n  dependency-type: direct:development\n  update-type: version-update:semver-minor\n  dependency-group: python-dev\n- dependency-name: ruff\n  dependency-version: 0.16.10\n  dependency-type: direct:development\n  update-type: version-update:semver-patch\n  dependency-group: python-dev\n- dependency-name: ty\n  dependency-version: 0.0.84\n  dependency-type: direct:development\n  update-type: version-update:semver-patch\n  dependency-group: python-dev\n...\n\nSigned-off-by: dependabot[bot] <support@github.com>\n\n* build(deps-dev): advance direct dependency floors\n\n* build(deps-dev): align ruff hook with project version\n\n* build(deps-dev): sync lock requirement metadata\n\n---------\n\nSigned-off-by: dependabot[bot] <support@github.com>\nCo-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>\nCo-authored-by: Jamie Nelson <stack@bitflight.io>",
          "timestamp": "2026-10-06T15:02:42Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/a08c63f2cec8ed1c7f999ba294e0b8d607c6598d"
        },
        "date": 1791299137801,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 4748.602,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 5035.99,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 5573.102,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 198.769,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "279fd503080e7699020667fe4d5b07172c4d1103",
          "message": "feat(cli): add structured JSON output for agent consumers (#330)\n\n* feat(cli): add typed JSON response layer\n\n* feat(cli): add typed JSON response layer\n\n* test(cli): add JSON contract coverage\n\n* test(cli): add JSON contract coverage\n\n* test(cli): add JSON contract coverage\n\n* test(cli): add JSON contract coverage\n\n* test(cli): add JSON contract coverage\n\n* feat(cli): integrate JSON responses\n\n* feat(cli): integrate JSON responses\n\n* feat(cli): integrate JSON responses\n\n* refactor(scan): expose validation results for structured output\n\n* feat(cli): integrate structured JSON output\n\n* docs(cli): document machine-readable JSON output\n\n* docs(cli): document machine-readable JSON output\n\n* fix(cli): wrap complete help to terminal width\n\n* test(cli): require width-aware complete help\n\n* test(json): restore contract support artifacts\n\n* test(json): restore contract support artifacts\n\n* test(json): restore contract support artifacts\n\n* test(json): restore contract support artifacts\n\n* test(json): restore contract support artifacts\n\n* test(json): restore contract support artifacts\n\n* test(json): restore CLI probe support\n\n* test(json): restore CLI probe support\n\n* test(json): restore CLI probe support\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* test(json): add response schema snapshots\n\n* fix(cli): preserve extracted validator ownership\n\n* test(help): expect wrapping without truncation\n\n* test(json): assert reversible serialization semantics\n\n* test(types): resolve CLI probe support modules\n\n* fix(cli): repair JSON integration seams\n\n* test(cli): align contracts with intentional wrapping and JSON escaping\n\n* test(cli): align contracts with intentional wrapping and JSON escaping\n\n* test(cli): align contracts with intentional wrapping and JSON escaping\n\n* test(cli): align contracts with intentional wrapping and JSON escaping\n\n* test(help): assert wrapped content without requiring word adjacency\n\n* test(help): assert wrapped content without requiring word adjacency\n\n* fix(cli): remove stale duplicate check command\n\n* fix(cli): restore structured rule response helpers\n\n* test(cli): repair malformed wrapping assertions\n\n* test(cli): repair malformed wrapping assertions\n\n* test(json): prove text visibility without forbidding richer machine output\n\n* test(help): assert readability and content preservation, not layout identity\n\n* test(help): remove redundant formatter-unit coverage\n\n* test(help): remove duplicate help-content scenario\n\n* test(json): name non-UTF8 tests for the actual contract\n\n* fix(help): wrap prose without splitting authored tokens\n\n* test(json): assert recovery metadata for remaining hidden info\n\n* test(json): drop POSIX surrogate tests pending explicit path encoding contract\n\n* test(help): preserve authored tokens across terminal widths\n\n* fix(help): use supported token-preserving wrapping\n\n* test(help): remove synthetic cross-width token equivalence\n\n* style: satisfy lint after help wrapping\n\n* style: document token-count return value\n\n* style: use generator annotation for context manager\n\n* style: clean JSON parity lint\n\n* style: remove obsolete help-test imports\n\n* style: sort scan runtime imports\n\n* style: sort help imports\n\n* style: sort CLI imports",
          "timestamp": "2026-10-07T11:22:33Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/279fd503080e7699020667fe4d5b07172c4d1103"
        },
        "date": 1791372359354,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 4631.935,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 4927.723,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 5461.512,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 203.136,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "1cbccf27e0bea04ab9d65058317b9dc7226feac2",
          "message": "fix(vendor-drift): keep usage errors off the drift exit code (#331)\n\n* fix(vendor-drift): keep usage errors off the drift exit code\n\nfetch_platform_docs.py exits 2 for detected vendor drift, and Click/Typer\nalso exit 2 for a usage error, so the SessionStart hook that acts only on\nexit 2 could not tell a malformed invocation from drift (#316).\n\nAdd main(), which re-reports a usage error as 64 (sysexits EX_USAGE) and\nleaves every other outcome unchanged. The drift code stays 2, so the hook,\ntests and docs that rely on it are unaffected.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(vendor-drift): show Click's usage text for usage errors\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n---------\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-10-09T11:04:18Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/1cbccf27e0bea04ab9d65058317b9dc7226feac2"
        },
        "date": 1791544049320,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 2447.938,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 2602.094,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 2899.395,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 384.69,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "ac7f10977672c31aaa4d0cdf2aac9e029d4d4ec7",
          "message": "fix(record): report unwritable --record targets and keep ANSI off --no-color stdout (#334)\n\nA --record path with an unsupported extension or a missing parent directory\nraised a traceback on the text path. It now exits 2 with the same one-line\nerror --json already gave, through one shared writer.\n\n--no-color --record still forced the terminal copy to ANSI, so bold and\nother attributes reached stdout. The recording console now forces a terminal\nonly when colour is on, as ConsoleReporter does. The SVG keeps its styles.\n\nFixes #314\nFixes #317\n\n\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-10-09T11:24:54Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/ac7f10977672c31aaa4d0cdf2aac9e029d4d4ec7"
        },
        "date": 1791545286537,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 4671.358,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 4922.889,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 5399.658,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 203.336,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "782353bbff0436added6e65b5c566e3acb053cda",
          "message": "fix(reporting): print diagnostic data literally, not as Rich emoji (#332)\n\n* fix(reporting): print diagnostic data literally, not as Rich emoji\n\nA line number that is also a Rich emoji code (:100:, :1234:) rendered as an\nemoji in ConsoleReporter output. rich.markup.escape protects \"[\" only, so\nevery string that mixed status-icon tokens with data was exposed: paths,\nfields, messages, URLs, validator names and fix descriptions.\n\nResolve the status icons to glyphs up front (output.emoji_glyph) and turn\nemoji replacement off on the data-carrying prints and on the consoles\n(reporter default, --record, rules, docs). Also escape the unknown rule id\nechoed by `skilllint rule`, which raised MarkupError for \"[/bold]\".\n\nFixes #327\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* test(reporting): drop unsourced bounds from the literal-text properties\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(output): measure panels with emoji replacement off, as they print\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n---------\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-10-09T11:47:28Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/782353bbff0436added6e65b5c566e3acb053cda"
        },
        "date": 1791546611163,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 2677.245,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 2937.737,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 3456.12,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 340.738,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "203fad5fedd68131874f0362f1ae14ac74776f27",
          "message": "fix(fix): follow a renamed skill folder through the rest of the --fix run (#335)\n\n* fix(fix): follow a skill folder renamed by --fix instead of crashing\n\nNameFormatValidator renamed violations--1 to violations-1, then later fixers\nand the post-fix revalidation still used the old SKILL.md path and raised\nFileNotFoundError. A fixer that moves its file now reports the new path\n(RelocatingFixer); apply_authorized_fixes hands it to later fixers and\nreturns it, and results and recorded fixes use the path that exists.\n\nWhen the second step of the two-step rename fails (target exists), the first\nstep is undone, so the folder is never left under its .fmtemp name.\n\nFixes #326\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): keep FixOutcome falsy when nothing applied and re-resolve config after a move\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): leave a skill folder that plugin.json registers unrenamed\n\nRenaming a folder listed under plugin.json skills left the manifest naming a\nmissing path (PR002) while --fix exited 0. The name fix now skips such a\nskill entirely, so its original findings stay reported.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): also keep a skill whose SKILL.md plugin.json registers directly\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): follow queued paths into a folder renamed earlier in the run\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): follow chained folder renames and case-only renames\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): detect folder moves from spelled paths, not existence or basenames\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): check every enclosing plugin.json and keep gitignored paths skipped after a move\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): rebase results collected before a folder moved\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* perf(fix): rebase moved paths with string prefixes, not Path.is_relative_to\n\nProfiling the 200-skill violations fixture showed the per-rename rebase\nhelpers at 2.2s cumulative; string prefix matching brings them to 0.18s.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): skip plugin.json skill entries that hold a NUL byte\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): keep a skill folder that plugin.json commands or agents register\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): read plugin.json registrations through a typed boundary and re-check gitignore after a move\n\nThe rename guard now takes component paths from\nboundary.plugin_level_config_ingest.ingest_plugin_component_paths, a\nTypeAdapter-validated reader of skills, commands and agents, instead of\nfiltering the raw manifest dict. A path rebased onto a renamed folder is\nasked against git's ignore rules again, from a scan base that still exists.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): preserve registrations across plugin layouts\n\nRead enclosing manifests from adapter-declared layouts and validate their component paths through the existing typed boundary. Preserve registrations that traverse the skill directory, including paths containing symlinks or parent-directory segments.\n\nCover default CLI behavior, mixed enclosing layouts, manifest cache separation, symlink registrations, and the path passed to later fixers.\n\n* fix(fix): follow '..' spellings of a renamed folder in queued paths\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): follow symlink aliases of a renamed folder in queued paths\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): preserve queued and reported identities across renames\n\nResolve parent traversals before mutation while preserving subsequent symlink entries. Snapshot queued identities and advance collected identities with each actual folder move, pairing spelled and canonical routes so aliases retain the originally selected file even when a later rename reuses the old target name.\n\nRetain the incoming lexical and symlink alias regression tests. Add coverage for already-collected aliases, directory-symlink traversal, preservation of a renamed symlink entry, and reused alias targets.\n\nValidation: 255 passed, 1 skipped in the combined affected regression suite; uv run prek run --all-files passed.\n\n* fix(fix): retain diagnostics after case-only folder renames\n\nRemove the old results entry before inserting the renamed key. Windows paths with different casing compare equal, so inserting first and then popping removes the same dictionary entry.\n\nAdd a host-independent regression using Windows path equality and separator semantics to preserve both the diagnostic list and the new key spelling.\n\nValidation: 162 relocation and scan-runtime tests passed; uv run prek run --all-files passed.\n\n* perf(fix): skip rename bookkeeping for paths a move cannot touch\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): follow queued file symlinks and keep old-path ignore probes across renames\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): preserve file targets and initial ignore decisions\n\nTrack file symlink targets consistently for queued and collected results while preserving directory entries for folder moves. Snapshot original ignore decisions before renames invalidate their probes. Retain incoming regressions and cover queued, collected, directory, and custom-ignore cases.\n\n* fix(fix): retain ignore decisions for original path spellings\n\nCapture custom ignore matches before normalizing parent traversal aliases. Track decisions by input index so a separately selected unignored canonical path still runs. Cover ignored-only input and both mixed-input orders with real CLI regressions.\n\n* fix(fix): find plugin manifests above a relative skill path\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01K5rAHJfvZyEEaUQghV7hCQ\n\n* fix(fix): match relocated paths with platform case rules\n\nUse normcase for containment while keeping destination spelling and original descendant components. Cover differently cased Windows queued and collected paths, and extend registered-skill CLI coverage to nested working directories across all supported manifests.\n\n---------\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-10-10T21:31:36Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/203fad5fedd68131874f0362f1ae14ac74776f27"
        },
        "date": 1791668083078,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 4700.005,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 4959.715,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 5466.839,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 201.826,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}