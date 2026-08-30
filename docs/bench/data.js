window.BENCHMARK_DATA = {
  "lastUpdate": 1788062913041,
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
          "id": "b30c12dff931361b49cd3a47f872e31a64ef7f4b",
          "message": "build(deps): bump the python-runtime group across 1 directory with 4 updates (#110)\n\nBumps the python-runtime group with 4 updates in the / directory: [gitpython](https://github.com/gitpython-developers/GitPython), [marko](https://github.com/frostming/marko), [tiktoken](https://github.com/openai/tiktoken) and [typer](https://github.com/fastapi/typer).\n\n\nUpdates `gitpython` from 3.1.58 to 3.1.60\n- [Release notes](https://github.com/gitpython-developers/GitPython/releases)\n- [Changelog](https://github.com/gitpython-developers/GitPython/blob/main/CHANGES)\n- [Commits](https://github.com/gitpython-developers/GitPython/compare/3.1.58...3.1.60)\n\nUpdates `marko` from 2.2.3 to 2.2.4\n- [Release notes](https://github.com/frostming/marko/releases)\n- [Changelog](https://github.com/frostming/marko/blob/master/CHANGELOG.md)\n- [Commits](https://github.com/frostming/marko/compare/v2.2.3...v2.2.4)\n\nUpdates `tiktoken` from 0.13.0 to 0.14.0\n- [Release notes](https://github.com/openai/tiktoken/releases)\n- [Changelog](https://github.com/openai/tiktoken/blob/main/CHANGELOG.md)\n- [Commits](https://github.com/openai/tiktoken/compare/0.13.0...0.14.0)\n\nUpdates `typer` from 0.27.0 to 0.27.1\n- [Release notes](https://github.com/fastapi/typer/releases)\n- [Changelog](https://github.com/fastapi/typer/blob/master/docs/release-notes.md)\n- [Commits](https://github.com/fastapi/typer/compare/0.27.0...0.27.1)\n\n---\nupdated-dependencies:\n- dependency-name: gitpython\n  dependency-version: 3.1.59\n  dependency-type: direct:production\n  update-type: version-update:semver-patch\n  dependency-group: python-runtime\n- dependency-name: marko\n  dependency-version: 2.2.4\n  dependency-type: direct:production\n  update-type: version-update:semver-patch\n  dependency-group: python-runtime\n- dependency-name: tiktoken\n  dependency-version: 0.14.0\n  dependency-type: direct:production\n  update-type: version-update:semver-minor\n  dependency-group: python-runtime\n- dependency-name: typer\n  dependency-version: 0.27.1\n  dependency-type: direct:production\n  update-type: version-update:semver-patch\n  dependency-group: python-runtime\n...\n\nSigned-off-by: dependabot[bot] <support@github.com>\nCo-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
          "timestamp": "2026-08-30T02:50:51Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/b30c12dff931361b49cd3a47f872e31a64ef7f4b"
        },
        "date": 1788058454095,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 15513.87,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 16156.07,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 17280.323,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 61.958,
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
          "id": "b9336318b9018bf2ca7b00f737fdf5047490f271",
          "message": "fix(lk,nr): correct NR002 citation, delete LK002, resolve ${CLAUDE_*} vars before LK001 (#122)\n\n* fix(nr): correct NR002 citation to the real path-traversal source\n\nNR002's authority cited agentskills.io/specification.md, which says\nnothing about traversal, boundaries, escaping, or symlinks (verified:\ngrep -ci for those terms returns 0 against the cached spec). The rule\nitself is correct; point it at code.claude.com/docs/en/plugins-reference's\n\"Path traversal limitations\" section instead, which documents exactly\nthe `..`, `/`, and `\\` rejections NR002 enforces.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(lk): delete LK002 -- upstream specs use bare relative links\n\nLK002 warned that relative markdown links need a ./ prefix. The\nAgentSkills specification's own worked example\n([the reference guide](references/REFERENCE.md)) and Anthropic's\nskills doc ([reference.md](reference.md)) both use bare links with no\n./ prefix (verified: zero `](./` occurrences in either cached doc).\nLK002 fired on both specs' own examples. Its docstring justification\nhad no source; the real ./-prefix requirement upstream applies to\nplugin.json manifest path fields, already covered by PL004.\n\nDeletes check_lk002, its registry entry, LK002's ErrorCode/alias, the\nLK002-emitting block in InternalLinkValidator.validate(), and its\ntests/fixtures. test_ignore_config_discovery.py used LK002 purely as a\nconvenient warning-level rule to exercise the generic suppression\nmechanism (not testing LK002 semantics) -- swapped to FM007. Updates\nREADME tables, plugin README, rule-catalog.md, and docs/ignore-config.md.\n\nTest count: -2 (TestMissingPrefixWarning class deleted; the ignore-config\nsuite's LK002-based tests were renamed to FM007, net 0 there).\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(lk): resolve \\${CLAUDE_*} substitution variables before LK001 (#111)\n\nLK001 flagged [text](\\${CLAUDE_PLUGIN_ROOT}/docs/foo.md) as a broken link\nbecause it treated the literal \\${CLAUDE_PLUGIN_ROOT} string as a\nfilesystem path. code.claude.com/docs/en/skills.md documents four\nsubstitution variables Claude Code expands in skill markdown content:\n\\${CLAUDE_SKILL_DIR}, \\${CLAUDE_PROJECT_DIR}, \\${CLAUDE_PLUGIN_ROOT}, and\n\\${CLAUDE_PLUGIN_DATA}.\n\nInternalLinkValidator now resolves the two variables it can determine\nstatically from the plugin source tree before the existence check:\n\\${CLAUDE_SKILL_DIR} (the SKILL.md's own directory) and\n\\${CLAUDE_PLUGIN_ROOT} (via find_plugin_dir -- same lookup\nHookValidator already uses for \\${CLAUDE_PLUGIN_ROOT} in hook commands).\n\\${CLAUDE_PROJECT_DIR} and \\${CLAUDE_PLUGIN_DATA} target install-time\nlocations that don't exist in the plugin source, and any other\nunrecognized \\${...} token has no documented meaning skilllint could\nresolve -- both are skipped rather than reported, since skilllint has\nno basis for asserting an unresolvable target is broken.\n\nTest count: +8 (TestClaudeVariableSubstitution).\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T03:04:50Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/b9336318b9018bf2ca7b00f737fdf5047490f271"
        },
        "date": 1788059281842,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14932.241,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15611.61,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16809.299,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 64.119,
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
          "id": "79aa3487fd38868edfb12b08f7f9e57bbb7a4d69",
          "message": "feat(policy): add configurable skill thresholds (#97)\n\n* fix(policy): address PR #97 review findings\n\n- #1: drop AS005 from the configurable threshold set (it shares the\n  SK006/SK007 token band and has no threshold plumbing of its own);\n  keep AS005 severity configurable\n- #2: reset both thresholds to defaults when SK006 >= SK007 so the\n  warning band stays reachable (matches test_limits.py invariant)\n- #3: guard severity values with isinstance(str) before set membership\n  so a composite value (list/dict) no longer raises TypeError and\n  aborts the run\n- #4: resolve and apply per-plugin policy in validate_file so the\n  --platform path honors the same thresholds as the default path\n- #5: thread a per-run policy cache through validate_single_path/scan\n  loop instead of a fresh {} per call\n- #6: document the numeric test literals in test_policy_config.py\n\nAlso: surface invalid config on stderr (once per config) instead of\nsilently defaulting, per docs/TYPING_POLICY.md (producer errors must\nnot be silently coerced). Bump ruff>=0.16.2, ty>=0.0.69 via uv.\n\n* fix(policy): address Codex re-review on a1f264f\n\n- Cache ancestor lookup during the policy walk so a sibling skill reuses\n  the already-cached ancestor instead of re-walking, re-reading config,\n  and re-emitting each diagnostic once per sibling\n- Apply resolved severity (not just thresholds) in the --platform\n  validation path so the two paths no longer lint the same skill\n  differently for configured AS005/SK006/SK007 severities\n\nAdds a sibling-cache-reuse regression test.\n\n* fix(policy): address Codex re-review on 4a33171\n\n- Report a diagnostic when a present policy section (thresholds/severity)\n  is not an object instead of silently defaulting\n- Thread the per-run policy cache into validate_file so --platform scans\n  reuse the shared cache instead of re-reading config and re-emitting\n  diagnostics once per file\n\nAdds regression tests for both.\n\n* fix(policy): share the per-run policy cache with nested Claude validation\n\nvalidate_file() normalised its policy cache inline for its own\n_resolve_policy() call but passed nothing to run_platform_checks(), whose\nClaude branch calls validate_single_path() with a fresh cache. A\n--platform claude-code scan therefore re-read each .skilllint.json /\nvalidator.json and re-emitted its invalid-policy diagnostics once per\nfile — twice for a single file, ~2000 times for a 1000-file scan.\n\nNormalise the cache once in validate_file() and thread it through\nrun_platform_checks() into the nested pipeline, restoring the\nonce-per-config diagnostic contract on the platform path.\n\nAlso reuse _VALID_SEVERITIES in the AS-series severity remap instead of\nrepeating the literal set.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T03:11:40Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/79aa3487fd38868edfb12b08f7f9e57bbb7a4d69"
        },
        "date": 1788059691968,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14959.533,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15626.764,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16867.318,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 64.057,
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
          "id": "988ac985dedbb89c497a3e82368555c4c0d7df1d",
          "message": "refactor(rules): route rule references through rule_reference, drop dead RuleEntry.fn (#103)\n\nEvery rules/*_series.py module carried a private `_docs_url(code)` wrapper.\n#108 reduced each of them to a one-line pass-through to\n`rule_registry.rule_reference`, leaving eight of the twelve with no call\nsites at all (#123). Delete all twelve and point the live call sites at\n`rule_reference` directly — it is already imported at module level and needs\nno deferred import to dodge the plugin_validator circular dependency. Where\nthat left an empty \"Spec sources\" banner, remove the banner too.\n\n`generate_docs_url` promised a bare code string in its docstring but not in\nits signature; widen the annotation to `ErrorCode | str` so the two agree.\nThat is what lets a rule module emit a finding for a code with no ErrorCode\nmember.\n\n`RuleEntry.fn` had no readers — the decorator stored the function and nothing\never retrieved it. Remove the field, its `Any` import, and the\n`arbitrary_types_allowed` config that existed only to carry it. Callers in\nthe test suite passed `fn=` into a model whose default `extra=\"ignore\"` would\nhave swallowed it silently, so drop those kwargs and the stub functions that\nexisted only to fill them.\n\nRefs #41\nCloses #123\n\n\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T03:32:17Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/988ac985dedbb89c497a3e82368555c4c0d7df1d"
        },
        "date": 1788060928313,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14796.093,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15510.991,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16610.426,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 64.535,
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
          "id": "48997a6c44bb1393d3030904ca5684da65816faa",
          "message": "refactor: fix orphaned Architecture citations, canonicalize thresholds, delete FM008 (#105)\n\n* fix(#40): citation cleanup — canonicalize thresholds, delete FM008, remove stale comments\n\nStep 1: Remove architecture line citations from plugin_validator.py and\nsk_series.py docstrings/comments (already done, uncommitted).\n\nStep 2: Make limits.py the canonical threshold source. token_counter.py now\nimports BODY_TOKEN_WARNING/BODY_TOKEN_ERROR from limits.py instead of\ndefining its own 4400/8800 literals. TOKEN_WARNING_THRESHOLD and\nTOKEN_ERROR_THRESHOLD are now aliases of the limits.py values.\n\nStep 3: Delete FM008 (Skills field not a YAML list) from RULE_REGISTRY.\nRemoved @skilllint_rule decorator, check_fm008 function, __all__ entry,\nimport in plugin_validator.py, call site, and test fixtures.\n\nStep 4: Remove stale comments referencing retired codes:\n- limits.py: Deleted 'AS Rules Reference' block (AS001-AS006)\n- token_counter.py: Updated threshold comments (removed AS005 refs)\n- fm_series.py: Updated severity docstring (removed FM008)\n- sk_series.py: Updated comment (removed AS001 ref)\n- plugin_validator.py: Updated docstrings (removed specific AS/SK code refs)\n\nVerified: uv run pytest (1136 passed, 1 skipped); ruff check (clean);\nty check (clean).\n\n* fix(#40): remove stale FM008 consumers left by the rule deletion\n\nFM008 (\"skills must be a YAML list of strings\") is gone from the registry\nand the validation pipeline, but its consumers still advertised it:\n\n- plugins/agentskills-skilllint/skills/skilllint/SKILL.md and\n  references/rule-catalog.md listed FM008 as a shipped, auto-fixable rule\n- scripts/generate_violations_fixture.py, bench_cpu.py and bench_profile.py\n  built and labelled FM008 violation cases\n- CLAUDE.md described the benchmark fixture as covering FM008\n\nThose benchmark cases never exercised FM008. Commit 5a88d60 (v1.6.1)\ninverted the rule from \"skills must be CSV\" to \"skills must be a YAML list\"\nbut left the fixture generator emitting `skills:` as a YAML list and calling\nit a violation — which the post-5a88d60 rule body accepted. The generator's\nFM008 and FM007+FM008 cases have produced zero FM008 findings since v1.6.1,\nso dropping them removes dead scenarios rather than real coverage.\n\ntest_rule_registry.py registered a synthetic RULE_REGISTRY[\"FM008\"] entry to\nexercise the unresolvable-relative-reference warning. Retitled to ZZ999 so a\nretired rule id is not reintroduced by a grep.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(#40): regenerate benchmark fixture and rules screenshot after FM008 deletion\n\nBoth artifacts are committed build outputs that no code regenerates, so the\nFM008 deletion left them advertising a rule skilllint can no longer run.\n\ntests/fixtures/benchmark-plugin-violations.zip — benchmark.yml extracts this\narchive directly and never invokes the generator, so editing VIOLATION_CYCLE\nalone left 40 of 200 skills carrying only the deleted FM008 pattern. The\ncommitted blob was stale in a second way as well: its FM007 cases used a\n`tools:` key, from a generator revision older than the switch to\n`allowed-tools:`. Regenerated from the current generator — 200 skills split\n67/67/66 across FM004/FM007/FM009.\n\nThe regenerated fixture exercises more, not less. Scanning the old archive\nyielded 40 FM004, 80 FM007 and 40 colon-parse findings (160 total); the 40\npure-FM008 skills produced nothing. The new archive yields 67 FM004, 67 FM007\nand 66 colon-parse findings (200 total). Both the compare-ref and base-ref\nbenchmark runs read a single extraction of the same archive, so the A/B\ncomparison stays valid across the change.\n\ndocs/screenshots/rules.svg — README.md:38 embeds this as the rule overview.\nRe-recorded through the same code path as `skilllint rules` at the file's\nexisting 100-column geometry. Drops the FM008 row, and also the LK002 row\nleft behind when #122 deleted that rule.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* style: trim trailing whitespace from regenerated rules.svg\n\nRich's `Console.export_svg` emits two lines with trailing whitespace, so every\nre-record reintroduces them. The `trailing-whitespace` pre-commit hook already\ntrims this on the way in — all five committed screenshots have zero such lines\non main — so no change to `record_export.export_recording` is warranted; the\nhook is the guard and it is self-healing on future regenerations.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* docs: note FM008 removal in the advertised FM rule ranges\n\nREADME.md and plugins/agentskills-skilllint/README.md both advertise\n\"FM001–FM010\", which now spans a gap: the series jumps FM007 to FM009. The\nadjacent AS row already discloses its gap as \"(AS007 removed)\", so the two\nrows read inconsistently otherwise. Applied the same annotation rather than\nsplitting the range, since the gap is interior and a range cannot express it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T03:44:24Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/48997a6c44bb1393d3030904ca5684da65816faa"
        },
        "date": 1788061639258,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 13492.26,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 14482.375,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 15799.878,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 69.118,
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
          "id": "f1f324315fe1fc40e0815bf180f2621cfc7fb567",
          "message": "refactor(rules): complete all 25 stub rule functions; validators become thin wrappers (#119)\n\n* refactor(rules): complete the check_* rule functions; validators become wrappers\n\nDetection for eight rule series moves out of the validator classes in\nplugin_validator.py and into the `check_*` functions in\npackages/skilllint/rules/*_series.py. Each validator keeps only what is\ngenuinely a validator concern -- reading the file, packaging issues into a\nValidationResult, and any auto-fix that mutates the filesystem -- and delegates\ndetection to the rule that owns the code and its documentation.\n\nSquashed from:\n\n- refactor(sl): complete check_sl001; establish the rule-migration pattern\n- refactor(nr): complete check_nr001/check_nr002; thin NamespaceReferenceValidator\n- refactor(lk): complete check_lk001; move link extraction into rules\n- refactor(pl): complete check_pl001-check_pl006; thin PluginStructureValidator\n- refactor(hk): complete check_hk001-check_hk005; HookValidator becomes a wrapper\n- refactor(pd): complete check_pd001-pd003; thin the validator\n- refactor(tc): complete check_tc001; MarkdownTokenCounter becomes a wrapper\n- refactor(pr): complete check_pr001-check_pr005; thin PluginRegistrationValidator\n- fix(rules): repair integration damage from merging eight parallel refactors\n- chore(skills): add receiving-pr-reviews and rebase skills, adapted for this repo\n- build: exclude vendored skills from ruff and from ty\n- fix: address Codex review on PR #119\n\nSquashed because the branch was invalidated by four separate merges to main\nwhile it was open; replaying fourteen commits meant resolving the same files\nagainst each of them in turn.\n\nCarried in from the review pass:\n\nhooks.json now enters through a typed boundary. `skilllint.rules` is not a\nboundary package, so decoding untrusted JSON there and narrowing it with\nisinstance checks violated docs/TYPING_POLICY.md 4-6. The decode lives in\n`skilllint/boundary/hooks_json_ingest.py`, which validates strictly with\nPydantic and returns a concrete `dict[str, JsonValue]` or a `HooksJsonDefect`.\nValidation stays shallow on purpose: HK002/HK003 exist to report on the nested\nhook groups, so validating them here would leave those rules nothing to say.\n\nIn the vendored receiving-pr-reviews script: GitHub response models inherit a\n`strict=True` base so producer-shape mismatches are rejected at ingress rather\nthan coerced; the unsourced `_MIN_POLL_BUDGET_SECONDS = 5.0` is deleted in\nfavour of `deadline` as the only cutoff, with a poll that fails at or past the\ndeadline classified as the window ending rather than an unconfirmed tail; the\n`watch` baseline diff keys on each thread's comment identity so a reply to a\nknown thread is detected; and `--interval-seconds` takes `min=1`.\n\nThe rebase skill now runs `git rebase <target> <branch>` instead of rebasing\nwhatever is checked out. `testpaths` gains `.agents/skills/*/scripts` so\nvendored-skill tests are collected in place, keeping that tree byte-identical\nto upstream.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix: address second Codex pass on the vendored skills\n\nFour P2 findings, all against `.agents/skills/`.\n\n`_GH_TIMEOUT_SECONDS = 30` is deleted. `gh api --paginate` fetches every page\nsequentially inside one subprocess, so that cap covered a whole pagination run\non an arbitrarily large PR over an arbitrarily slow link -- a number this\nrepository has no source for. The bound is now caller-derived: `fetch` and\n`watch` expose `--gh-timeout-seconds` (unbounded by default), and `watch`\nadditionally bounds each poll by its own `--timeout-seconds` deadline.\n\n`watch`'s mandatory baseline fetch is no longer deadline-bounded. With\n`--timeout-seconds 0` the deadline is already spent, so bounding the baseline by\nit floored the `gh` timeout and raised `TimeoutExpired` instead of producing the\ndocumented immediate snapshot. `--timeout-seconds` is also constrained to >= 0.\n\nThe receiving-pr-reviews SKILL.md gotchas promised a reserved final poll near\n`deadline`, which the previous commit removed along with the unsourced margin.\nCorrected to state what the loop actually does -- the last observed state can be\nup to one interval stale, and the step 7 loop is what covers the gap -- so an\norchestrating agent is not told a window was checked when it was not. The\nactivity-diff gotcha is corrected too: threads are compared by comment identity,\nnot by id, and reviews carry an id.\n\nThe rebase skill's `git rebase <target> <branch>` fails with `fatal: '<branch>'\nis already used by worktree at ...` when another worktree holds the branch --\nthe same multi-worktree scenario the surrounding text describes. Step 5 now says\nto locate the owning worktree with `git worktree list` and run the rebase there,\nand warns against freeing the branch by disturbing that worktree.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T04:05:29Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/f1f324315fe1fc40e0815bf180f2621cfc7fb567"
        },
        "date": 1788062912475,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14801.467,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15262.235,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16140.835,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 65.587,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}