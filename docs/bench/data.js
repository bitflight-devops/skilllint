window.BENCHMARK_DATA = {
  "lastUpdate": 1788058082417,
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
          "id": "fbc35365697cff850d1f9350326e234fc9360c2c",
          "message": "style: apply Ruff formatting to policy changes",
          "timestamp": "2026-08-07T09:34:41Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/fbc35365697cff850d1f9350326e234fc9360c2c"
        },
        "date": 1786325425139,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 16339.478,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 17209.772,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 18791.224,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 58.165,
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
          "id": "8c334f1f351a256174350f30e238bd9406e5f3f8",
          "message": "fix(rules): derive finding references from rule codes; correct AS001/AS007 (#108)\n\n* fix(rules): derive finding references from rule codes; correct AS001/AS007\n\nFindings printed a hardcoded URL into a third-party repository\n(jamie-bitflight/claude_skills ERROR_CODES.md). skilllint ships as\n`uvx skilllint@latest`, so every user of the published CLI got a pointer\ninto one specific consumer's repo. Replace it with `skilllint rule <CODE>`,\nderived from the rule code so it cannot drift and resolves for any user.\n\nThe URL literal was duplicated across 13 files; all now route through a\nsingle rule_reference() in rule_registry.py. ERROR_CODE_BASE_URL and the\ntwelve _XX_DOCS_BASE constants are removed.\n\n25 rules (hk, pl, pr, pd, lk, nr, sl, tc) cited that same URL as their\nauthority `reference`. The dead reference is dropped and `origin` kept, so\nthe missing citation is visible rather than hidden behind a link that was\nabout to 404. Those rules still need real upstream authorities.\n\nAS001 emitted \"name field is missing\" from a rule that is otherwise a name\n*format* check, duplicating FM001 on agent files. Scope the presence check\nto SKILL.md: FM001 deliberately does not fire for skills, since skills.md\nmarks `name` optional with a directory-name fallback, so deleting the branch\noutright would have removed the only missing-name signal there.\n\nAS007 claimed wildcard entries \"will not resolve\" and that \"the agent\nreceives no MCP tools\". Both are false for a server-scoped grant:\n`mcp__<server>__*` resolves to every tool that server exposes, identically\nto the bare `mcp__<server>` form the rule already accepted. Flagging one\nspelling while passing an equivalent one pushed authors between two forms\nwith the same outcome. AS007 now fires only on unscoped wildcards (`*`,\n`mcp__*`), with the message and docstring corrected. Sourced to this repo's\nvendored Anthropic docs (claude_code/CHANGELOG.md, plugin-dev\nmcp-integration/references/tool-usage.md).\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as007): cite the doc that defines `tools:`; split severity by launch impact\n\nAS007 cited agentskills.io /specification#tools-field as its authority. Fetched\nthe spec rather than assuming: it defines no `tools` field, has no #tools-field\nanchor, and mentions \"mcp\" zero times. Its only tool field is a space-separated\n`allowed-tools`, whose own example is `Bash(git:*) Bash(jq:*) Read` — itself a\nwildcard. The words \"wildcard\", \"pattern\", \"exact\" and \"glob\" do not appear.\nThat spec cannot be the authority for a rule about wildcard tool entries.\n\n`tools:` is Claude Code subagent frontmatter, so cite the doc that defines it.\nsub-agents.md on the `tools` field: \"If no entry in the list resolves to a\ntool, the subagent usually fails to launch with an error naming the entries.\"\n\nThat sentence also corrects the severity. A single unresolvable entry is\ndropped and the surviving entries still grant the subagent its tools; only an\nentirely unresolvable list is fatal. Erroring on one unscoped wildcard beside\nvalid entries was a false positive. AS007 now warns in that case and errors\nonly when nothing in the list can resolve.\n\n    mcp__Ref__*        clean    (server-scoped grant)\n    mcp__Ref           clean\n    mcp__*, Read       warning  (Read resolves; subagent launches)\n    mcp__*             error    (nothing resolves; fails to launch)\n    \"*\"                error\n\nBoth source documents are reproducible offline via `skilllint docs fetch`;\n.claude/vendor is a gitignored cache, so they are cited by URL, not vendored.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as): scope the AS family to SKILL.md; agent files are not AgentSkills\n\nThe AgentSkills specification is a cross-harness baseline for SKILLS. It\ndefines SKILL.md and does not describe agent files at all. Two call sites\nrouted agent files into the AS family anyway:\n\n  _get_validators_for_path: file_type in {SKILL, AGENT}\n  run_platform_checks:      is_skill_md(path) or \"agents\" in path.parts\n\nSo AS rules were evaluating agent frontmatter — a category error by\nconstruction, independent of whether any individual check was accurate. Both\nsites are now SKILL.md only.\n\nThis is the root cause of the two bugs fixed earlier in this branch, not a\nthird bug. AS001 double-reported a missing `name` alongside FM001 because it\nwas reading agent files it should never have seen; AS007 asserted claims about\n`tools:`, a field the AgentSkills spec does not define, for the same reason.\nAS002 already carried its own hand-written agent-file suppression — three\nrules, three separate guards, one missing boundary. The next AS rule would\nhave needed a fourth.\n\nWith the boundary in the family, AS001's per-rule guard is redundant and is\nremoved; it reverts to reporting a missing name unconditionally, which is\ncorrect now that it only ever sees a SKILL.md.\n\nAS007 survives here in its corrected form, but it is checking a Claude Code\nfield from a family that no longer runs on Claude Code agent files, so it is\nnow effectively dead for its original target. Whether it should be deleted or\nrebuilt in a series that governs agent files is left as a follow-up rather\nthan decided in a bugfix.\n\nThe new tests assert the routing through _get_validators_for_path rather than\ncalling AsSeriesValidator directly — a direct call bypasses the boundary and\npasses even when the wiring is wrong, which is exactly how the previous\nagent-file test kept passing after the wiring changed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as007): a wildcard server segment is not a group grant\n\nReview catch. The exemption pattern was `^mcp__.+__\\*$`, whose `.+` also\nmatched `mcp__*__*` and `mcp__foo*__*`. Those name no concrete server, so\nnothing resolves and the subagent cannot launch — exactly the case AS007\nexists to catch — yet they were being treated as valid server-scoped grants\nand passed silently.\n\nRestrict the server segment to non-wildcard characters: `^mcp__[^*]+__\\*$`.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as007): stop the server capture spanning `__`; stop overclaiming survival\n\nTwo more review catches, both mine.\n\nThe exemption pattern `^mcp__[^*]+__\\*$` let `[^*]+` span an extra `__`\nseparator, so `mcp__Ref__tool__*` was exempted as a server-scoped grant. `Ref`\nis a real server, so AS008 passed it too. But that entry places the wildcard\ninside a tool name rather than forming the documented `mcp__<server>__*` group\ngrant. Server names may contain single underscores (`plugin_dh_backlog`) while\n`__` terminates the segment, so the capture is now\n`[^*_]+(?:_[^*_]+)*` — single underscores allowed, `__` not.\n\n    mcp__Ref__*                exempt\n    mcp__plugin_dh_backlog__*  exempt\n    mcp__a_b_c__*              exempt\n    mcp__Ref__tool__*          flagged\n    mcp__*__*                  flagged\n    mcp__foo*__*               flagged\n\nSecond: the warning branch asserted \"the remaining entries still resolve\".\nskilllint cannot know that — it has no registry of live tool names. For\n`tools: [NoSuchTool, \"*\"]` nothing resolves and the subagent fails to launch,\nwhile the message claimed the grant survived and downgraded to a warning.\n\nFatality is only provable in one direction: when every entry is an unscoped\nwildcard, nothing can resolve. Severity keeps that conservative split, but the\nmessage no longer claims what it cannot check — it now says the entry\ncontributes no tools and that the subagent fails to launch if no other entry\nresolves either.\n\nAsserting an unverifiable consequence is the exact defect this branch exists\nto remove, so it should not have shipped in a message this branch added.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as): delete AS007; point AS008 at the field the spec actually defines\n\nCloses the loop opened by scoping the AS family to SKILL.md.\n\n`_extract_tools_list` read only `parsed.get(\"tools\")`. With the family now\nSKILL.md-only, AS007 and AS008 were reading a field the AgentSkills\nspecification does not define for skills while blind to `allowed-tools`, the\none it does. Both rules validated nothing: a SKILL.md with\n`allowed-tools: mcp__*` produced no violation at all.\n\nAS007 is deleted rather than repointed. Its authority covered agent `tools:`,\nwhich this family no longer validates; its family covers SKILL.md, where its\nlogic has no authority — the spec says nothing about wildcard resolution and\nits own example is a wildcard (`allowed-tools: Bash(git:*) Bash(jq:*) Read`).\nThere is no field where it is both in-family and in-authority. Aiming it at\n`allowed-tools` would have been another rule shipped ahead of its source,\nwhich is the defect this branch exists to remove.\n\nThat also resolves two review findings against AS007's exemption pattern and\nits fatality heuristic by removing the code they were about.\n\nAS008 is the opposite case and survives with real reach. Server-name casing is\nexact and case-sensitive, and there is a live instance the rule could not see:\n`allowed-tools: mcp__ref__*` for a server registering as `Ref`. It now reads\n`allowed-tools`, with `_extract_tools_list` taking the field name as a\nparameter.\n\nThe inline form is split on whitespace AND commas. The spec describes\n`allowed-tools` as space-separated (agentskills.io/specification.md, fetched\n2026-08-22, sha256 2b1dbb4f…89e40d) but marks it Experimental with support\nvarying between implementations, and nothing establishes another separator is\nan error. Parsing liberally is what lets the rule see entries either way;\nreporting a separator would be a new unsourced rule and is not added.\n\nAgent `tools:` remains unvalidated — tracked in #109. PA-series is the natural\nhome, but it is wired at plugin-directory level rather than per-file, so giving\nit a per-file mode is a design decision, not a bugfix.\n\ndocs/registry-schema-examples.md keeps AS007 as a worked example of what an\nempty `references` list predicts: it was the signal, five months before anyone\nchecked.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T02:44:41Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/8c334f1f351a256174350f30e238bd9406e5f3f8"
        },
        "date": 1788058081656,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 15638.873,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 16409.398,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 17756.079,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 61.002,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}