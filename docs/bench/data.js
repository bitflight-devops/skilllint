window.BENCHMARK_DATA = {
  "lastUpdate": 1785989775992,
  "repoUrl": "https://github.com/bitflight-devops/skilllint",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "97def80d24e767b6a6594b2b2b2e47fd425ebf8b",
          "message": "fix(ci): switch benchmark-action to auto-push, remove broken manual commit step\n\nThe manual 'Commit updated benchmark data' step was using\n'git push origin HEAD' to push docs/bench/ to the current branch,\nbut with auto-push:false the action writes data to gh-pages locally\n(not the main working tree), so 'git add docs/bench/' always found\nnothing and the push was a no-op at best.\n\nFix: set auto-push:true on all three Store steps so the action\nmanages its own gh-pages commit/push atomically. Remove the now-\nredundant manual commit step from both benchmark-io and\nbenchmark-release jobs.",
          "timestamp": "2026-03-18T18:50:35Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/97def80d24e767b6a6594b2b2b2e47fd425ebf8b"
        },
        "date": 1773859871123,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "cpu_clean_mean_ms",
            "value": 0.532482,
            "unit": "ms"
          },
          {
            "name": "cpu_violations_mean_ms",
            "value": 0.721954,
            "unit": "ms"
          },
          {
            "name": "cpu_fix_mean_ms",
            "value": 1.865923,
            "unit": "ms"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "97def80d24e767b6a6594b2b2b2e47fd425ebf8b",
          "message": "fix(ci): switch benchmark-action to auto-push, remove broken manual commit step\n\nThe manual 'Commit updated benchmark data' step was using\n'git push origin HEAD' to push docs/bench/ to the current branch,\nbut with auto-push:false the action writes data to gh-pages locally\n(not the main working tree), so 'git add docs/bench/' always found\nnothing and the push was a no-op at best.\n\nFix: set auto-push:true on all three Store steps so the action\nmanages its own gh-pages commit/push atomically. Remove the now-\nredundant manual commit step from both benchmark-io and\nbenchmark-release jobs.",
          "timestamp": "2026-03-18T18:50:35Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/97def80d24e767b6a6594b2b2b2e47fd425ebf8b"
        },
        "date": 1773859912556,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 9048.378,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9106.586,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 9172.34,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 109.92,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "97def80d24e767b6a6594b2b2b2e47fd425ebf8b",
          "message": "fix(ci): switch benchmark-action to auto-push, remove broken manual commit step\n\nThe manual 'Commit updated benchmark data' step was using\n'git push origin HEAD' to push docs/bench/ to the current branch,\nbut with auto-push:false the action writes data to gh-pages locally\n(not the main working tree), so 'git add docs/bench/' always found\nnothing and the push was a no-op at best.\n\nFix: set auto-push:true on all three Store steps so the action\nmanages its own gh-pages commit/push atomically. Remove the now-\nredundant manual commit step from both benchmark-io and\nbenchmark-release jobs.",
          "timestamp": "2026-03-18T18:50:35Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/97def80d24e767b6a6594b2b2b2e47fd425ebf8b"
        },
        "date": 1773859996732,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 9025.202,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9583.03,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 10653.449,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 104.455,
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
          "id": "546b05ac9b7e43625352768b4f2b1b863b5fb1d3",
          "message": "fix: add httpx dependency and fix test fixtures for CI green (#23)",
          "timestamp": "2026-03-24T02:30:28Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/546b05ac9b7e43625352768b4f2b1b863b5fb1d3"
        },
        "date": 1774319596141,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14820.393,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15229.892,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16042.105,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 65.726,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "ad9fd96ba48e200abdaadc09c46efd34b98b2040",
          "message": "fix: move ignore patterns from invented .markdownlintignore to .markdownlint-cli2.jsonc\n\n.markdownlintignore was not a valid config file. Patterns moved to the\nignores array in .markdownlint-cli2.jsonc where they belong.",
          "timestamp": "2026-03-24T12:36:46Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/ad9fd96ba48e200abdaadc09c46efd34b98b2040"
        },
        "date": 1774355992827,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14373.215,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 14892.401,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 15891.21,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 67.215,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "662935bd1bc23951705dcb9ded8f2b40a25e2a68",
          "message": "fix: restore FM004/FM010 routing, coerce ValidationIssue for Pydantic, ty-clean tests\n\n- FM004: detect block-scalar descriptions in raw YAML (folded strings lack newlines)\n- FM010: directory/name mismatch is a warning; invalid patterns stay errors\n- Rebuild issues via ValidationIssue.model_validate in _build_validation_result to\n  avoid model_type failures when running python -m skilllint.plugin_validator\n- Thread frontmatter_text into check_fm004; satisfy ty in tests (cast, assert, ty: ignore)",
          "timestamp": "2026-03-27T14:08:08Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/662935bd1bc23951705dcb9ded8f2b40a25e2a68"
        },
        "date": 1774621065214,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14644.386,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15186.098,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16266.304,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 65.916,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "cd4507d92593472f851d762bf5d40edbfa6f29b2",
          "message": "refactor: clarify typing policy and boundary validation guidelines\n\n- Enhanced the typing policy section to specify restrictions on the use of `cast()` and the treatment of raw external payloads.\n- Introduced a structured approach for handling type checking and validation, emphasizing the use of `@no_type_check` for exceptions.\n- Updated references to the TYPING_POLICY document for consistency and clarity in coding standards.",
          "timestamp": "2026-03-27T14:22:13Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/cd4507d92593472f851d762bf5d40edbfa6f29b2"
        },
        "date": 1774621639136,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 15270.716,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15969.644,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 17180.945,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 62.681,
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
          "id": "5a88d60c29864a620ff567223fde4810638336d3",
          "message": "fix(fm008,as008): remove FM008 rule; fix AS008 plugin-prefix false positives (#27)",
          "timestamp": "2026-03-29T02:49:37Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/5a88d60c29864a620ff567223fde4810638336d3"
        },
        "date": 1774752766117,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 16585.772,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 17356.956,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 18267.536,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 57.671,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Copilot",
            "username": "Copilot",
            "email": "198982749+Copilot@users.noreply.github.com"
          },
          "committer": {
            "name": "GitHub",
            "username": "web-flow",
            "email": "noreply@github.com"
          },
          "id": "f232002ce5bb435b184159a00ff68430e1461bd6",
          "message": "feat: add GitHub Action for skilllint validation (#33)",
          "timestamp": "2026-04-11T08:00:39Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/f232002ce5bb435b184159a00ff68430e1461bd6"
        },
        "date": 1775894620251,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14973.667,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15559.422,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16721.193,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 64.334,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "aa8e6ebf1b50e0709c1737b2c7a1474ad1e4520d",
          "message": "fix(type): improve the typer Path imports",
          "timestamp": "2026-04-14T13:56:59Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/aa8e6ebf1b50e0709c1737b2c7a1474ad1e4520d"
        },
        "date": 1776175225771,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 15104.493,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15721.073,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16639.809,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 63.672,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "3ae22370d246805a20b42e2e01029a4abe1fbed7",
          "message": "feat(config): add .skilllint.json ignore config with upward discovery and caching\n\nExtends suppression to work outside plugin contexts. Previously,\nper-rule suppression only applied inside .claude-plugin/ plugins.\n\n- Add .skilllint.json support: walk up from each scanned file to find\n  the nearest config file (.claude-plugin/validator.json or .skilllint.json)\n- Ignore keys: \"\" suppresses globally, path prefixes scope suppression\n  to matching files relative to the config file location\n- Cache discovered config per directory within a single run so shared\n  parent directories are only walked once across all expanded paths\n- Plugin-level .claude-plugin/validator.json takes priority when inside\n  a plugin; .skilllint.json is used otherwise\n- Fix PLC1901: prefix == \"\" → not prefix\n- Add 21 tests covering discovery, caching, global/scoped suppression,\n  and end-to-end validate_single_path integration\n- Update README and add docs/ignore-config.md reference",
          "timestamp": "2026-04-14T17:51:27Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/3ae22370d246805a20b42e2e01029a4abe1fbed7"
        },
        "date": 1776189283977,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 15565.009,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 16389.735,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 17417.669,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 61.075,
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
          "id": "29643fae9ed3a3ebf370f37c607a215deaa29b4e",
          "message": "ci: add custom_release_rules for refactor and perf commits (#79)\n\n* ci: replace broken release job with python-semantic-release auto-publish\n\nThe previous release pipeline had two problems:\n- mathieudutour/github-tag-action with default_bump=false ignored all\n  build/ci/chore commits (every commit since v1.8.0), so no tag was\n  ever created and the release step was always skipped\n- ncipollo/release-action used secrets.RELEASE_TOKEN which is not\n  configured, so even when a tag was created the release step failed\n  and the publish.yml release-event trigger never fired\n\nReplace with auto-publish.yml that:\n- Triggers via workflow_run after the Test workflow passes on main\n  (so tests must be green before any release attempt)\n- Uses python-semantic-release/action@v9 which honours the existing\n  [tool.semantic_release] config in pyproject.toml\n- Publishes to PyPI via uv publish (OIDC) in the same job, removing\n  the need for RELEASE_TOKEN or a cascade through publish.yml\n\nAlso tighten test.yml permissions to contents: read now that the\nrelease job is gone.\n\nNOTE: PyPI trusted publishing must be updated to include\n.github/workflows/auto-publish.yml for uv publish to succeed.\n\nhttps://claude.ai/code/session_018zrrSiajwwRwBc2UHsV6sE\n\n* ci: fix auto-publish to use RELEASE_TOKEN and preserve existing OIDC chain\n\nThe April 14 run (24414443253) that produced v1.8.0 shows the full\nworking chain: RELEASE_TOKEN creates the GitHub release → release:published\nfires → publish.yml → existing PyPI OIDC trusted publisher.\n\nRemove uv publish from auto-publish.yml (it would require a new PyPI\ntrusted publisher entry and bypass the already-configured publish.yml\nOIDC setup). Use RELEASE_TOKEN for both checkout and PSR github_token\nso the release event cascades to publish.yml exactly as before.\nDrop the unnecessary id-token: write permission.\n\nhttps://claude.ai/code/session_018zrrSiajwwRwBc2UHsV6sE\n\n* ci: revert to minimal fix — swap tag action in existing release job\n\nRemove the auto-publish.yml structural redesign (not warranted by\nthe evidence) and restore the release job in test.yml. The only\nconfirmed issue was mathieudutour/github-tag-action@v6.2 with\ndefault_bump: false producing an empty new_tag for commits without\nfeat:/fix:/perf: prefixes, observed in run 27387601460.\n\nReplace the two old steps (github-tag-action + ncipollo/release-action)\nwith python-semantic-release/action@v9 using RELEASE_TOKEN, which\nreads bump rules from [tool.semantic_release] in pyproject.toml.\nEverything else (permissions, workflow structure, publish.yml, OIDC)\nis left exactly as it was on main.\n\nhttps://claude.ai/code/session_018zrrSiajwwRwBc2UHsV6sE\n\n* ci: add custom_release_rules for refactor and perf commits\n\nmathieudutour/github-tag-action@v6.2 with default_bump: false only\nrecognises feat:/fix: by default. The project's pyproject.toml already\ndeclares refactor and perf as patch-bump triggers in patch_tags, but\nthe action was unaware of them. After v1.8.0 (April 14), all merged\ncommits used refactor:, build:, ci:, or no prefix — none recognised,\nso no tag was produced and publish.yml never triggered.\n\nAdding custom_release_rules aligns the action with the project's\ndeclared bump rules. No other changes.\n\nhttps://claude.ai/code/session_018zrrSiajwwRwBc2UHsV6sE\n\n* docs: add diagnostic discipline rules to CLAUDE.md\n\nTwo rules derived from the auto-publish investigation: compare failing\nruns to successful runs before diagnosing, and implement the smallest\ndiff that addresses the observed failure.\n\nhttps://claude.ai/code/session_018zrrSiajwwRwBc2UHsV6sE\n\n---------\n\nCo-authored-by: Claude <noreply@anthropic.com>",
          "timestamp": "2026-06-13T17:19:00Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/29643fae9ed3a3ebf370f37c607a215deaa29b4e"
        },
        "date": 1781371346811,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 16814.116,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 17383.861,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 17934.645,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 57.582,
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
          "id": "7d244c8f20939f38f376a3689946b4e370d9904a",
          "message": "feat(scan): support skill-folder scanning (#95)\n\n* fix: discover folder-backed skills in scan runtime\n\n* feat(scan): validate skill folders\n\n* test(scan): align folder target expectations\n\n* fix: address PR 95 review findings\n\n* fix: normalize ignored skill folder paths\n\n* fix(scan-runtime): normalize skill targets",
          "timestamp": "2026-08-06T04:13:20Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/7d244c8f20939f38f376a3689946b4e370d9904a"
        },
        "date": 1785989775225,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11967.049,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 12828.896,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 14444.04,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 78.027,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}