window.BENCHMARK_DATA = {
  "lastUpdate": 1788674238002,
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
          "id": "e393337a2fcbf163815b11ae0e195a2b54452373",
          "message": "fix: address third Codex pass on PR #119 (#134)\n\nThree findings that landed after #119 was merged, so they come as a follow-up.\n\n`_thread_activity_key` missed edits. An edit to an existing inline comment\nchanges neither its `databaseId` nor the thread's `comments_total`, so `watch`\ncould report `timed_out: true` while revised feedback sat unread. The key now\ncarries each comment's body as well. Three kinds of change have to register and\nno single component catches all three: a reply adds an id, an edit changes only\nthe body, and a reply past the query's `comments(first: 100)` page changes only\nthe untruncated `comments_total`.\n\nA non-zero `gh` exit is no longer excused by the clock. The previous commit\nclassified a poll that failed at or past `deadline` as the window ending, but\napplied that to `CalledProcessError` too. Only a timeout can be explained by the\nshrinking budget; an authentication, rate-limit, API or GraphQL error cannot, and\nreporting `timed_out: true` from stale state after one would tell a caller the PR\nis clean when nothing was checked. The handlers are now separate.\n\nThe Hypothesis strategies in test_hooks_json_ingest.py carried `max_size=16` and\n`max_size=8` with no source, which is the repository's own \"No invented\nconstraints\" rule -- and they narrowed the coverage the property claims. Removed;\nHypothesis's own default sizing governs, and the docstring says why.\n\n\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T04:19:05Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/e393337a2fcbf163815b11ae0e195a2b54452373"
        },
        "date": 1788063728696,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 14883.961,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 15466.314,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 16510.68,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 64.721,
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
          "id": "30bc6d339335b3e11706e729d504c9f6538aba67",
          "message": "refactor: rule de-duplication + authority split (Workstream B) (#102)\n\n* test: freeze rule deduplication expectations\n\n* feat(policy): delete AS004 parser heuristic\n\n* refactor(rules): retire AS005 token emission\n\n* refactor(rules): consolidate name format ownership\n\n* test: update assertions for retired name rules\n\n* refactor(rules): delete retired name rule implementations\n\n* refactor(rules): retire AS003 missing description\n\n* feat(schemas): add provenance registry and opinion catalog JSON files\n\nprovenance-registry.json: 4 vendor-backed claims (AS001.max_name_length,\nHK002.valid_event_types, HK003.valid_hook_types, FM007.tool_field_names).\n\nopinion-catalog.json: 7 unbacked lint opinions (SK006/SK007 thresholds,\nSK004 min description length, SK005 trigger phrases, AS007 wildcard safety,\nFM004 multiline YAML, AS001 regex pattern + consecutive-hyphen rule).\n\nWorkstream B Task 6.\n\n* docs: update stale references from retired rule codes (AS001→FM010, AS002→FM010, SK001-3 removed)\n\n* style: ruff format -- check fixes for 4 files\n\n* style: biome format opinion-catalog.json reference array\n\n* fix(fm010): restore command coverage and the auto-fix path\n\nFM010 reporting moved into a file-type-independent check so commands/*.md\nregain name-format validation: CommandFrontmatter declares no 'name' field,\nso the Pydantic pattern constraint never covered it. SK008 stays skill-only\nin its own helper.\n\nNameFormatValidator returns as a fix-only participant via\n_get_fixers_for_path. It holds the only FM010 repair (name normalisation and\nskill directory rename); removing it from the pipeline had removed the fix\nentirely, because FrontmatterValidator._compute_normalized_fixes bails on\nValidationError before fix_skill_name_field() is reached.\n\nOne reporter, one fixer, still exactly one FM010 finding per file.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(as001): keep the missing-name signal, scoped to presence only\n\nPR #108 added an AS001 branch for a SKILL.md that declares no name, with\nthe rationale that FM001 stays silent there: agentskills.io requires the\nfield, Claude Code's skills.md treats it as optional, so\nSkillFrontmatter.name is 'str | None'. This branch's de-duplication had\ndeleted AS001 outright and taken that unique signal with it.\n\nAS001 comes back asserting presence only. Name syntax -- casing, hyphens,\nlength, and the directory match -- stays FM010's, so nothing duplicates.\n\nAlso un-hides three assertions that the retirement commits had renamed to a\nleading underscore, which stopped pytest collecting them.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(provenance): give each claim a real owner and a loadable locator\n\nReview findings from PR #102, validated against the code:\n\n- provenance-registry.json: the max_name_length claim moves from AS001 to\n  FM010, which is what reads _MAX_NAME_LENGTH now. AS001 asserts presence\n  only and makes no length claim.\n- provenance-registry.json: FM007's assertion_location pointed at prose and\n  a line number that had already drifted. fm_series now names the field set\n  _TOOL_FIELD_NAMES so a drift check can load the symbol.\n- opinion-catalog.json: the name-pattern opinion moves to FM010 and drops\n  stale line numbers; the AS007 entry goes, since PR #108 deleted the rule.\n- maintainer-extension-guide.md: the FM010 examples showed a signature and\n  an authority the code does not use. Corrected, and the guide now states\n  that rule-level authority is coarser than claim-level provenance, with\n  FM010's own split across the two catalogs as the worked example.\n- rule-catalog.md: FM001 was listed as an AS rule; the AS table now lists\n  the rules that exist, with the retirements noted below it.\n\nProvenance in output: FM findings carried no authority at all, so the tests\nasserting it had been reduced to 'code == FM010'. rule_authority() moves to\nrule_registry (as_series kept a private copy), run_platform_checks attaches\nit, and the three assertions come back asserting populated origin and\nreference.\n\nAlso: the FM010 packaging assertion passed on any nonzero exit; the FM005\nrule-truth assertion was 'len(...) >= 0'; and built_wheel reused whatever\nwheel sat in dist/, so these tests could assert against an older commit.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* test(policy): AS005 severity override is now a rejected key\n\nPR #97 added test_as005_severity_is_configurable while AS005 still existed.\nThis branch retires AS005 into SK006/SK007, so a config naming it must be\nreported rather than accepted as an override for a rule that emits nothing.\nThe configurable-severity case moves to SK006, which still emits.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(fix-path): reuse reporting validators and stop the name fix eating the delimiter\n\nTwo follow-up review findings on the fix-only validator wiring:\n\n- _get_fixers_for_path rebuilt the validator list, so FrontmatterValidator.fix()\n  queued its FM009 info on a throwaway instance and the revalidation never\n  reported the repair. It now takes the reporting instances and appends to them.\n- NameFormatValidator._try_fix_name_format rebuilt the file as\n  '---\\n{frontmatter}{body}' where body already starts past the closing\n  delimiter, so every repaired file lost its closing '---' and came back as\n  FM003. Pre-existing on main; restoring this fixer would have restored the\n  corruption. Regression test added.\n\nThe FM007 provenance claim cited agentskills_io/v1.json but pointed at a symbol\nholding three fields, only one of which that schema defines. Split into\n_AGENTSKILLS_TOOL_FIELD_NAMES ('allowed-tools') and\n_CLAUDE_CODE_TOOL_FIELD_NAMES ('tools', 'disallowedTools'); the claim now\nresolves to the former, so a drift comparison sees the field set its authority\nactually declares.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(validate): restore cross-platform skill checks and colon diagnostics\n\nSix review findings, all reproduced before fixing:\n\n- A SKILL.md validated under Cursor, Codex or no adapter reported only AS006.\n  Those adapters never run FrontmatterValidator, so AS001-AS003 and AS005 were\n  the only checks on that path and retiring them left nothing. The canonical\n  owners now run there: FM010, FM001's description claim, and the SK006/SK007\n  token band via ComplexityValidator.\n- FM002 was suppressed whenever any adapter matched, including Cursor and Codex\n  which never report it. It now keys on whether the frontmatter pipeline will\n  actually run, via the same predicate.\n- Colon recovery was silent on a check-only run: safe_load_yaml_with_colon_fix\n  quotes the value in memory and returns no YAML error, and only the fix path\n  queued FM009. FM009 is now emitted as a warning when recovery was needed, and\n  the same gap on the PA001 plugin-agent ingestion path is closed.\n- SK004-SK007 declared an anthropic.com authority while opinion-catalog.json\n  records all four as having no upstream source. With authority now reaching\n  violation output, that presented repository heuristics as vendor\n  requirements. The authority kwarg is dropped from those four rules.\n- FM007's Claude-specific fields had no catalog entry after the provenance\n  split. The tools field is in claude_code/v1.json, disallowedTools is in no\n  packaged schema, so the pair is recorded as an opinion rather than a claim that could\n  never be compared.\n\nvalidate_file lost its dead sk_validators computation and the SKILL.md block\nmoved into _skill_md_violations, which is what the locals count was signalling.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(validate): keep a missing skill description an error off the pipeline\n\ncheck_fm001 grades a skill description as a warning because skills.md calls\nit Recommended. The shared cross-platform path runs only where no adapter\napplies that reading, and the AgentSkills specification the AS series\nenforces marks description Required -- which is why the retired AS003\nemitted an error there. Grading it a warning let violations_to_result mark\nan invalid file as passed and the CLI exit 0.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(provenance): stop three claims asserting more than their source says\n\nThree review findings on provenance correctness, each checked against the\nsource rather than the code that reads it:\n\n- FM001 registered the sub-agents page and FM010 the skills page, but both\n  rules fire for skills, agents and commands. With authority now reaching\n  violation output, an FM001 on a SKILL.md cited the agent docs and an FM010\n  on an agent cited the skill docs. Neither rule can name one correct page,\n  so both register origin alone; the per-context sources stay in the\n  docstrings that `skilllint rule <CODE>` renders, and per-claim URLs stay in\n  the provenance registry where claim-level provenance belongs.\n\n- HK003 claimed the hook-development page as the authority for\n  VALID_HOOK_TYPES, while design-rule-provenance-registry.md line 11 already\n  said no vendor file enumerates that set. The page lists command and http;\n  the constant also holds prompt and agent. The claim moves to the opinion\n  catalog, and the worked example in registry-schema-examples.md keeps its\n  shape with a note recording why it is not shipped.\n\n- SK004 enforces a 1024-character maximum that is schema-backed\n  (agentskills_io/v1.json, description maxLength) but had no claim, so the\n  constant could drift silently while the catalog recorded only the unsourced\n  20-character minimum. Added SK004.max_description_length against\n  DESCRIPTION_MAX_LENGTH, and scoped the opinion key to\n  SK004.min_description_length so the split is legible.\n\ntest_authority_reference_is_url asserted a URL on FM010 specifically. It now\nasserts the invariant across the whole registry: any declared reference is an\nabsolute URL or a rooted path, and declaring none is allowed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(fm010,fm004): restore the directory-match error, drop FM004's vendor claim\n\n- FM010's directory-mismatch finding was a warning while AS002 carried the\n  same AgentSkills invariant as an error. Retiring AS002 left a SKILL.md whose\n  name differs from its directory passing on every selection, including\n  claude_code, where main failed it. The finding is now an error, so FM010\n  fully absorbs the claim it inherited rather than half of it.\n\n  test_mismatched_name_raises_validation_warning encoded the warning grade; it\n  now asserts the error and records why. The FM004/FM007 severity-routing test\n  wrote its SKILL.md straight into tmp_path, so the incidental directory\n  mismatch would have masked the severities under test -- it now writes into a\n  matching directory.\n\n- FM004 still declared an anthropic.com authority while opinion-catalog.json\n  records it as a style preference the runtime accepts. Same defect as\n  SK004-SK007 earlier in this review; same fix.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(validate,provenance,docs): close six follow-up review findings\n\nValidation:\n- Colon recovery had no reporter off the Claude pipeline either. The shared\n  SKILL.md path discarded parse_skill_md's colon_fields, so a --platform\n  cursor/codex run reported nothing for a source that only parsed after\n  quoting. It now emits the same FM009 warning the pipeline does.\n- The shared findings bypassed the ignore config entirely: _resolve_policy\n  already loads policy.ignore and its root, but the violations were appended\n  straight to the output. They are now filtered with _is_suppressed, so the\n  --platform route and the default path agree on what a config suppresses.\n\nProvenance:\n- HK002 claimed the hook-configuration-formats section as authority for the\n  whole event set, while design-rule-provenance-registry.md records that 12 of\n  the 21 names have no traceable source. Moved to the opinion catalog, as HK003\n  was earlier in this review, with the design doc quoted as the rationale.\n- Both hook claims located their constants on HookValidator; PR #119 moved them\n  to module level in rules/hk_series.py. The references now name the real\n  symbols.\n- SK004 compares frontmatter_core.RECOMMENDED_DESCRIPTION_LENGTH, which was an\n  independent 1024 literal that merely matched limits.DESCRIPTION_MAX_LENGTH.\n  Both frontmatter_core constants now alias the limits constant, so the claim's\n  locator is the value SK004 actually enforces and the duplicate cannot drift.\n\nDocs:\n- The root README still advertised SK001-SK009 and used SK001 in a rule\n  example, both of which now return \"Unknown rule\". rule_registry's own\n  docstring examples cited SK001 too. All three screenshots were stale in two\n  ways -- retired codes and pre-#103 ERROR_CODES URLs -- and are regenerated\n  with skilllint --record.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* docs(authority): make the FM010 guide example context-neutral\n\nThe maintainer guide still passed _SKILLS_SPEC_URL in both FM010 examples\nafter the decorator dropped it, so copying one would reattach the skills\npage to agent and command findings -- the misattribution just removed from\nthe code. Both examples now declare origin alone, and the note below them\nexplains rule-level authority is coarse in two ways rather than one: a rule\nserving several file types cannot name one page, and a rule can mix sourced\nand unsourced claims.\n\nAlso trims trailing whitespace the CLI's --record writes into the\nregenerated screenshots, which the trailing-whitespace hook rejected.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T04:41:48Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/30bc6d339335b3e11706e729d504c9f6538aba67"
        },
        "date": 1788065064797,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 8902.998,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9530.759,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 10747.2,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 105.028,
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
          "id": "728d7ae60a91ce7bb5664da1288ba1d0114de7cc",
          "message": "fix(PL006): stop --fix from silently rewriting valid marketplace.json (#141)\n\n* fix(PL006): stop --fix from silently rewriting valid marketplace.json\n\n`skilllint check --fix` was relocating documented root-level\n`description`/`version` fields into `metadata`, rewriting valid\nmarketplace.json files with no output and exit 0. The relocation writer\n(`_fix_marketplace_json_metadata_keys`) is deleted rather than repaired:\nits `NotImplementedError` guard on unknown keys was the only thing\nstopping its hardcoded three-key rebuild from dropping `$schema`,\n`renames`, and other unlisted keys, so widening the allowlist first\nwould have converted a false positive into real data loss.\n\n`MARKETPLACE_JSON_ROOT_KEYS` is widened only after the writer is gone,\nto the full documented root-key set (name, owner, plugins, metadata,\n$schema, description, version, allowCrossMarketplaceDependenciesOn,\nrenames), each with a source comment citing the vendored marketplace\nschema doc. `PluginStructureValidator.can_fix()` now returns False, so\nthe amplifier (--fix invoking every validator's fix() regardless of\nwhether it reported anything) can no longer run this writer on files\nPL006 never flagged.\n\nSeverity stays `error` per the issue's explicit constraint, even though\na live `claude plugin validate` v2.1.251 run against an unrecognized\nmarketplace root key returned a warning, not an error -- reported\nseparately rather than acted on, since downgrading was out of scope.\n\nCloses #114\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(PL006): preserve recognized metadata in the manual-correction guidance\n\nCodex flagged that deleting the relocation auto-fix carried its data-loss\nrisk into the diagnostic text: `repository`/`homepage`/`license`/`author`/\n`keywords` are documented plugin-manifest and marketplace `plugins[]`-entry\nfields, so a user who followed the (previous) \"remove or rename\" guidance\nfor one of these at the marketplace root would discard real data by hand\ninstead of by `--fix` -- the exact outcome #114 exists to prevent.\n\nReinstates `MARKETPLACE_METADATA_RELOCATABLE_KEYS` and the two-list return\nfrom `analyze_marketplace_root_keys`, used only to word PL006's message --\n`can_fix()` stays False and there is still no writer. The `metadata`\ndestination is documented honestly as not independently spec-verified: a\nlive `claude plugin validate` v2.1.251 run puts `metadata.repository` in\nthe same \"Unknown field ... ignores it at load time\" warning bucket as a\nbare root `repository`. `metadata` is suggested only because it is a\nstrictly less destructive manual home than deletion, sourced to the\ndeleted `_fix_marketplace_json_metadata_keys` rather than presented as\nspec-derived, per the \"no invented constraints\" project rule.\n\nAlso fixes a latent str.capitalize() bug the reinstated code path would\nhave reintroduced: capitalize() lowercases everything after the first\ncharacter, which would corrupt a user's own camelCase key name embedded\nin the suggestion text.\n\nAddresses PR #141 review thread (comment 3888921733, pl_series.py:626).\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T09:24:23Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/728d7ae60a91ce7bb5664da1288ba1d0114de7cc"
        },
        "date": 1788082032852,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11025.538,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11653.9,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12763.744,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.894,
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
          "id": "e1d7dc13902234b796472b73b6e93bf0cbc9a9a2",
          "message": "feat(rules): add AG series for agent frontmatter (tools/skills) (#147)\n\n* feat(rules): add AG series for agent frontmatter (tools/skills)\n\nCloses the gap left by PR #108 scoping the AS family to SKILL.md only:\nagents/*.md tools and skills fields had no validation at all.\n\n- AG001: every entry in an agent's `tools` field is a provably-unresolvable\n  wildcard (e.g. `tools: mcp__*`) -- ports AS007's deleted logic, authority\n  moved from agentskills.io to sub-agents.md#available-tools.\n- AG002: MCP server-name casing in `tools`/`disallowedTools` -- ports AS008's\n  discovery logic (extracted into rules/_mcp_tool_discovery.py, now shared\n  with AS008 on SKILL.md's allowed-tools) to agent files.\n- AG003: `skills` must be a YAML list, per sub-agents.md's own example --\n  the field FM008 used to check before being deleted in #105 for running on\n  the wrong file type.\n\nAlso fixes the model these rules depend on (#132):\nAgentFrontmatter.skills was `str | None` with list->CSV coercion,\ncontradicting the YAML-list shape sub-agents.md documents. It is now\n`list[str] | None`. The now-unnecessary --fix workaround that restored the\noriginal `skills` value to defeat that coercion is scoped to FileType.SKILL\nonly (SkillFrontmatter.skills still coerces, unaffected by this change).\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* fix(agent): align skills validation with runtime\n\n* fix(rules): narrow AG001 wildcard scope, fix AG002 discovery false-accepts\n\nAddresses four Codex review threads on PR #147:\n\n- AG001 (P1, thread PRRT_kwDORXxKvc6dgksB): only the literal `mcp__*` is\n  sourced to fail per sub-agents.md (\"Available tools\" -- `mcp__*` is\n  defined only for `disallowedTools`; in `tools` it matches neither\n  documented grant pattern). The prior regex flagged any unrecognized\n  wildcard-bearing token as fatal by default (e.g. `Bash(git:*)`), which is\n  the exact \"absence of documented meaning as proof of invalidity\" mistake\n  #108 deleted AS007 for. Narrowed to an exact-literal check; bare `*` is\n  also no longer flagged since neither is sourced.\n\n- Shared MCP analyzer (P2, thread PRRT_kwDORXxKvc6dgksD): the wildcard skip\n  lived in analyze_mcp_tool_reference itself, silently losing AS008's\n  \"unknown server\" diagnostic for `allowed-tools: mcp__*` on SKILL.md (a\n  regression from the pre-PR behavior). The analyzer now returns a\n  distinguishable \"unscoped\" status; AS008 reports it like any unknown\n  server (restoring prior behavior), AG002 skips it (AG001 owns that\n  diagnostic for agent files).\n\n- Plugin-namespaced resolution (P2, thread PRRT_kwDORXxKvc6dgksF):\n  resolve_plugin_namespaced_server returned a server name whose membership\n  the caller then checked against the *global* known-servers set, so a\n  same-named server from a different plugin or project config could\n  false-accept a namespaced reference the matched plugin does not itself\n  declare. It now also returns that plugin's own server set, and the\n  analyzer resolves membership/casing against it instead of the global set.\n\n- Plugin-agent frontmatter discovery (P2, thread PRRT_kwDORXxKvc6dgksH): a\n  plugin-packaged agent's own `mcpServers` field was feeding server\n  discovery, even though pa_series.py documents that Claude Code ignores\n  that field when loading an agent from a plugin. Excluded via a new\n  _is_plugin_packaged_agent check mirroring PA001's own definition.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T11:55:52Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/e1d7dc13902234b796472b73b6e93bf0cbc9a9a2"
        },
        "date": 1788091111293,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 9905.586,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 10567.344,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 11756.041,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 94.726,
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
          "id": "24b2bb640349e1f3045af4d1728ce9fa556b4a9e",
          "message": "fix(ty): move script-mode extra-paths config into the script itself (#157)\n\nPR #154 fixed ty's inability to resolve test_pr_review_threads.py's\nsibling `import pr_review_threads` by adding --extra-search-path to\nthe pre-commit hook's entry: line. That only helped when ty is\ninvoked through that one hook -- a direct `uv run ty check .agents/`\nstill failed, and every other caller (CI, editors) would need to\nre-know the flag.\n\nPEP 723 script metadata is TOML and accepts arbitrary [tool.*]\ntables. Verified empirically (ty 0.0.75) that ty reads a\n[tool.ty.environment] table declared inside the script's own\nmetadata block even in single-file script mode, and that relative\nextra-paths there resolve against the script's own directory (not\ninvocation cwd, not project root) -- so extra-paths = [\".\"] is the\nsibling directory ty needs.\n\nMove the config into the script's PEP 723 block so it travels with\nthe file for every caller, and drop the now-unneeded CLI flag from\nthe pre-commit hook.\n\n\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T12:49:39Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/24b2bb640349e1f3045af4d1728ce9fa556b4a9e"
        },
        "date": 1788094339577,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11097.309,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11734.378,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12923.523,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.305,
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
          "id": "5224488329243c71f1c5d261177a2bae3273adad",
          "message": "feat(receiving-pr-reviews): surface PR reviewability in fetch/watch (#159)\n\nA draft or conflicting PR never receives reviews, so unresolved_count: 0\nin that state means \"nothing can happen yet\", not \"nothing to do\" — the\nsame misleading-empty-result trap the reviews_count/threads_count triple\nalready warns about. Add reviewability (is_draft, mergeable,\nmerge_state_status, blockers) to FetchResult, derived from isDraft/\nmergeable/mergeStateStatus folded into the existing reviewThreads query\n(no extra gh round trip). mergeable: UNKNOWN is never reported as a\nblocker, since GitHub computes it asynchronously and returns UNKNOWN\nright after a push.",
          "timestamp": "2026-08-30T13:56:36Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/5224488329243c71f1c5d261177a2bae3273adad"
        },
        "date": 1788098359835,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 8623.908,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9157.014,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 10163.783,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 109.315,
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
          "id": "4d76204b4e7dd1366ef8a15d71b14aaa641702ea",
          "message": "refactor: drop the leading underscore from GitHubResponseModel (#160)\n\nThe class is the declared ingress boundary for every model built from raw\n`gh` output — the thing a reader needs to find to answer \"what is validated\nstrictly, and why\". Marking it module-private hid the one name that\ndocuments that contract.\n\nRename only; no behaviour change.\n\n\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-30T14:23:10Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/4d76204b4e7dd1366ef8a15d71b14aaa641702ea"
        },
        "date": 1788099941243,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 8759.346,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9230.547,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 9976.582,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 108.444,
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
          "id": "6ce225a9ba2c199b3362365c36a99f4f18ef64e3",
          "message": "feat(receiving-pr-reviews): add a checks command for PR CI status (#167)\n\nAn agent following this skill had no way to ask whether a PR's checks were\ngreen, so it hand-wrote polling loops instead — one with a glob that never\nmatched, one with an unsatisfiable jq filter, and one with no sleep at all,\nwhich exhausted GitHub's secondary rate limit while the primary buckets still\nread 5000/5000. Separately, a PR that appeared stalled for 30+ minutes was\nactually conflicting: GitHub runs no workflows on a conflicting PR, and the\nexisting `reviewability` signal that said so was discarded by a caller piping\nthe output through a field extractor.\n\n`checks --pr N` prints one compact object: `status` (passed / failed / pending\n/ none — a pending run and a green run are different values), `required_only`,\n`total`, the `failed` and `pending` check names, `contexts_truncated`, and the\nsame `reviewability` object `fetch` already reports, so `none` on a draft or\nconflicting PR is distinguishable from a repository with no CI. With\n`--timeout-seconds` it polls on the existing 90s interval and stops early when\n`reviewability.blockers` says no check can start.\n\nWhich checks gate the merge comes from GitHub's own\n`isRequired(pullRequestNumber:)` on the head commit's rollup — computed\nserver-side from the branch protection rule or ruleset covering the base\nbranch — rather than a hardcoded check-name list, and without the admin\npermission the branch-protection REST endpoint needs. Grading follows\nGitHub's documented rule that a required check must be successful, skipped, or\nneutral.\n\n\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-31T03:28:57Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/6ce225a9ba2c199b3362365c36a99f4f18ef64e3"
        },
        "date": 1788147098878,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11070.197,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11642.426,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12533.589,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.979,
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
          "id": "575b51782edecd3492a2e492db98967283a67dbb",
          "message": "fix(pr-reviews): make `checks` wait through the states it was returning on (#172)\n\n* fix(pr-reviews): make `checks` wait through the states it was returning on\n\nThree defects Codex raised on PR #167, four minutes after it merged.\n\n`status: \"none\"` was never polled. The loop continued only on `\"pending\"`,\nbut a just-pushed head commit reports a null `statusCheckRollup` until\nGitHub registers the workflow runs the push triggered, which grades as\n`\"none\"` — so `checks --timeout-seconds 270` returned that first snapshot\ninstantly, at exactly the moment SKILL.md step 3 tells the reader to run\nit. A `\"none\"` now gets one re-poll of grace. That bound introduces no\nduration of its own: the wait is one `--interval-seconds`, the unit the\ncaller already chose, so a repository with genuinely no CI settles after\none extra interval instead of spinning out the whole window.\n\nThe draft blocker short-circuited the wait, on a claim that is false for\nworkflows. Any non-empty `reviewability.blockers` ended the loop, citing\n\"reviewers are not requested until the PR is marked ready\" — a statement\nabout reviews. GitHub does run workflows on a draft PR unless a workflow\nopts out, and this repository's own `test.yml` and `benchmark.yml` trigger\non a bare `pull_request` with no `types:` filter and no draft guard. Only\nthe conflicting blocker stops CI, and `checks_blocked` is now the one\nplace that distinction is made. The false claim is corrected in the\n`checks` docstring and in SKILL.md, where both said GitHub runs no\nworkflow on a draft or a conflicting PR; only the conflicting half is true.\n\nThe verdict and the reviewability came from two unlinked head reads.\n`_CHECKS_QUERY` and `_HEAD_STATE_QUERY` each ran their own\n`commits(last: 1)`, neither selected `oid` and nothing compared them, so a\npush landing between the two calls produced a result pairing one head's\nrollup with another head's PR state. They are now one query over one\n`pullRequest` snapshot — following the reasoning the comment above\n`_HEAD_STATE_QUERY` already made — which removes the race outright and\ncosts `checks` one fewer `gh` call than comparing two `oid`s would.\n\nEach defect has a test that fails before the fix and passes after.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n* feat(pr-reviews): tell a stale Codex approval from no approval at all\n\nA review sweep reported `codex_approved: false` on a PR whose Codex 👍 was\nplainly present, and diagnosed it as the login match missing the `[bot]`\nsuffix. That diagnosis is wrong: `_CODEX_REACTOR_LOGINS` already holds both\nspellings, the lookup is lowercased, and a test already asserts it. The\nobservation was real, though. On Jamie-BitFlight/mkapidocs#26 the reaction\nlanded at 03:37:24Z and the head commit `d546671` was committed at\n03:40:38Z, so a push invalidated the approval three minutes later and the\nstaleness rule correctly refused to report it as current.\n\nThe defect is that the answer was unreadable, not that it was wrong. One\nboolean collapsed two situations calling for opposite actions: \"Codex has\nnot looked yet\" means keep waiting, \"Codex approved code that is no longer\non the branch\" means stop waiting and re-request a review. `fetch` now\nreports `codex_approval_stale` alongside `codex_approved` — mutually\nexclusive by construction — plus `codex_approved_at` and\n`latest_revision_at`, the two timestamps the verdict was computed from, so\na caller can say how stale rather than only that it is.\n\n`has_outstanding_work` deliberately still keys on `codex_approved` alone: a\nstale approval is a signal that expired, not one that arrived, and\nreturning on it would make `watch` exit immediately and forever on any PR\nwhose approval a push invalidated. A test pins that.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01QJeBLNA9ybmQvv5REMDkrc\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-31T08:02:50Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/575b51782edecd3492a2e492db98967283a67dbb"
        },
        "date": 1788163537149,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 9717.918,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 10287.647,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 11421.973,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 97.301,
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
          "id": "1e37b4a6c8a2ab9e144bfa4f4a5778e5c94ee028",
          "message": "fix: address top code-review findings from this week's changes (#174)\n\n* fix: address top code-review findings from this week's changes\n\n- Apply frontmatter-exemption check to the --fix path so exempt files\n  (e.g. AGENTS.md) aren't rewritten\n- Split HK005 warnings from errors so warning-only issues don't flip\n  passed=False\n- Guard scripts/uvu's `uv remove` so a new (undeclared) dependency\n  doesn't abort `set -eu` before `uv add` runs\n- Catch subprocess.TimeoutExpired in pr_review_threads._owner_repo\n- Null-guard c.user in post_coverage_summary.mjs for deleted accounts\n- Fix pr_series path normalization (.removeprefix over .lstrip) for\n  paths like ../shared/cmd.md\n- Consolidate the duplicated _make_issue helper across the *_series\n  rule modules into rule_registry.py\n- Cache repeated ancestor-directory plugin.json/.mcp.json walks with\n  functools.cache\n- Parallelize pr_review_gh.py's independent gh calls via\n  ThreadPoolExecutor\n\nVerified: uv run prek run --all-files and uv run pytest both pass\n(1488 passed, 10 skipped, 86.36% coverage).\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XXp48LEDndUtAWJe1nDtgd\n\n* fix: address PR review feedback on hook docstring and concurrent fetch\n\n- HookValidator.validate() docstring described HK004/HK005 as sharing\n  one list; the implementation already splits HK004 (hard error) into\n  errors and HK005 (warning) into warnings, with passed driven by\n  errors only. Update the docstring to match.\n- _fetch_concurrently used `with ThreadPoolExecutor(...) as executor:`,\n  whose __exit__ calls shutdown(wait=True) and blocked a failing gh\n  call's exception behind any still-running sibling call. Replace with\n  an explicit try/finally that shuts the pool down with\n  wait=False, cancel_futures=True, so a failure surfaces without\n  waiting on stragglers. Add a regression test exercising the fail-fast\n  path.\n\nAddresses PR #174 review feedback.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XXp48LEDndUtAWJe1nDtgd\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-01T07:48:55Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/1e37b4a6c8a2ab9e144bfa4f4a5778e5c94ee028"
        },
        "date": 1788249105924,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 12208.102,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 12748.647,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 13704.44,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 78.518,
            "unit": "files/s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "stack@bitflight.io"
          },
          "committer": {
            "name": "Jamie Nelson",
            "username": "Jamie-BitFlight",
            "email": "stack@bitflight.io"
          },
          "id": "3c8d8d1a00fa8fdaef932c024fb1e3b46d7e408a",
          "message": "feat(receiving-pr-reviews): add GitHub MCP fallback path\n\nDocument the lightweight GitHub-MCP-tool fallback for when the bundled\n`gh`-based helper isn't usable, mirroring the addition made in\nskill-lapidary and claude_skills.",
          "timestamp": "2026-09-03T04:26:49Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/3c8d8d1a00fa8fdaef932c024fb1e3b46d7e408a"
        },
        "date": 1788409765191,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 7976.07,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 8542.773,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 9578.903,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 117.175,
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
          "id": "9e676fc7a750519a8d926a7867703580035c84ec",
          "message": "fix(HK002,HK003): sync valid event/hook-type sets to hooks.md (#183)\n\n* fix(HK002,HK003): sync valid event/hook-type sets to hooks.md (#112)\n\nVALID_EVENT_TYPES held 22 event names; the cached hooks reference\n(code.claude.com/docs/en/hooks.md, \"Hook events\" level-3 headings)\nenumerates 31 — a strict subset, zero removals. Missing: CwdChanged,\nDirectoryAdded, FileChanged, MessageDisplay, PermissionDenied,\nPostToolBatch, Setup, TaskCreated, UserPromptExpansion. A plugin\nregistering any of those got an error today.\n\nVALID_HOOK_TYPES lacked mcp_tool, documented in the same doc's \"Common\nfields\" table alongside command/http/prompt/agent. mcp_tool requires\ntwo fields (server, tool) rather than one, so\n_REQUIRED_FIELD_BY_HOOK_TYPE widens from dict[str, str] to\ndict[str, tuple[str, ...]] and _check_hook_entry loops over the\nrequired fields instead of checking a single one.\n\nMove HK002.valid_event_types and HK003.valid_hook_types from\nopinion-catalog.json to provenance-registry.json: both rows asserted\n\"no vendor document enumerates this set\", which is false now that the\ncurrent hooks doc does. PR1's locator+value test pins both sets going\nforward. Update docs/registry-schema-examples.md's worked HK002/HK003\nexamples, which were marked NOT SHIPPED and cited a superseded vendor\npath.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* docs: mark HK002/HK003 resolved in the provenance design doc\n\nCode review on #179 found the design doc's problem-statement examples\nstill asserted HK002/HK003 have no traceable vendor source, directly\ncontradicting registry-schema-examples.md (updated by this same PR),\nwhich correctly marks both claims shipped with a real vendor source.\nAnnotated both bullets as resolved rather than rewriting the historical\naudit findings, since the original numbers (21/9/12, the four-type set)\nare what motivated the design and are still accurate as of that audit.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-04T05:11:14Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/9e676fc7a750519a8d926a7867703580035c84ec"
        },
        "date": 1788498894723,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 8812.626,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9468.388,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 10407.349,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 105.72,
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
          "id": "b503b719ad145f52e494a0fe999ab19c80a7d376",
          "message": "refactor(FM010): import MAX_NAME_LENGTH from _spec_constants (#41) (#184)\n\nfm_series.py duplicated _spec_constants.MAX_NAME_LENGTH as a local\n_MAX_NAME_LENGTH = 64 literal. as_series.py has no equivalent constant\n(AS001 only asserts name presence), so fm_series.py was the one\nremaining series still carrying its own copy after #69e5e77 introduced\n_spec_constants as the canonical source.\n\nImports the constant directly rather than via a deferred import inside\nthe one function that uses it (check_fm010), since _spec_constants has\nno skilllint-internal imports and so carries none of the circular-import\nrisk that motivates this module's other deferred imports.\n\nRepoints provenance-registry.json's FM010.max_name_length locator at\nthe canonical definition (_spec_constants.py) instead of the now-deleted\nlocal alias.\n\n\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-04T05:25:42Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/b503b719ad145f52e494a0fe999ab19c80a7d376"
        },
        "date": 1788499707296,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 10234.379,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 10932.615,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12063.519,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 91.561,
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
          "id": "bcdfd3222784940eec91154e4860f1884b968a1a",
          "message": "feat(AG): close the #109 follow-up cluster (#150, #149, #151, #153) (#185)\n\n* fix(AG001): detect unconditionally-removed tool names as provable-zero (#150)\n\n#109's analysis defined the provable-zero set for an agent tools: list\nas unscoped wildcards and/or the documented unconditional first-filter\nremoval list. #147 shipped only the wildcard half.\n\nSourced the removal list from sub-agents.md, \"Available tools\":\n\"The first filter removes these tools, even when listed in the tools\nfield:\" followed by a bullet list of nine names. Excluded Agent\n(removed only at the subagent depth limit) and ExitPlanMode (removed\nunless permissionMode is plan) since both are conditional and not\nprovable from frontmatter alone -- exactly the exclusion #150\nspecified. The remaining seven (AskUserQuestion, EndConversation,\nEnterPlanMode, ScheduleWakeup, TaskOutput, WaitForMcpServers, Workflow)\nmatch #150's proposed list exactly.\n\nAG001 now fires when every tools entry is either an unresolvable\nwildcard or one of these seven names, with a distinct message and fix\nsuggestion per failure reason. Added unit coverage for all seven names\nindividually, the two conditional exclusions staying clean, a mixed\nwildcard+removed-tool case, and a removed-tool-alongside-a-real-tool\ncase staying clean (skilllint has no live tool registry, so a sibling\nentry's resolution can't be proven either way). Added a fixture-driven\nfailing example alongside the existing wildcard one.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* refactor(AgentFrontmatter): type skills as JsonValue, not bare object (#149)\n\nAgentFrontmatter.skills was object | None, a bare catch-all forbidden\nby docs/TYPING_POLICY.md §3 outside boundary modules; frontmatter_core.py\ndoes not match any approved boundary naming convention (§6).\n\nFirst attempt reused plugin_validator.py's hand-rolled recursive\nYamlValue TypeAlias by moving it into frontmatter_core.py. That broke:\nPydantic cannot build a schema for an implicit recursive TypeAlias used\nas a model field under `from __future__ import annotations` -- it hits\nRecursionError at class-definition time (a documented Pydantic 2.13\nlimitation; its own error message points at PEP 695 type aliases,\nwhich need Python 3.12+ and this project supports 3.11+). Reverted that\nand used pydantic.JsonValue instead, Pydantic's own fast-pathed\nrecursive-value type built for exactly this case -- already used the\nsame way in rules/hk_series.py, so this isn't a new pattern.\n\nScope: only the `skills` field named in #149. AgentFrontmatter's other\nAny-typed fields (mcp_servers, hooks) and the sibling models' similar\nfields are out of scope -- larger retyping the issue itself frames as\nan open design question, not this fix's ask.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* fix(SkillFrontmatter): remove skills field and its CSV coercion (#151)\n\nVerified agentskills.io's packaged schema defines exactly six SKILL.md\nproperties (name, description, license, compatibility, metadata,\nallowed-tools); `skills` is not among them. It is documented only as\nsubagent frontmatter (sub-agents.md), the same reason FM008 was\ndeleted in #105 for asserting a `skills` shape on SKILL.md.\n\nRemoved SkillFrontmatter's explicit `skills: str | None` field and its\ninclusion in normalize_comma_separated. model_config.extra = \"allow\"\nnow captures an authored `skills:` key untouched -- no CSV coercion of\na YAML list, the same silent-mutation class #147 fixed for\nAgentFrontmatter. Verified nothing reads SkillFrontmatter.skills as a\ntyped attribute (grep -rn '\\.skills\\b' finds only the unrelated\nAgentFrontmatter/manifest hits).\n\nConfirmed the field-level fix does not change --fix output:\n_normalize_tool_fields_and_detect_changes already restores the raw\nparsed `skills` value into the fix output regardless of Pydantic\ncoercion (plugin_validator.py:2245-2246), so the field's own CSV\ncoercion only affected direct model_dump() consumers, not --fix. Added\na model-level regression test (not a --fix-level one, which would not\nhave discriminated) confirming both list and scalar skills values\nsurvive SkillFrontmatter.model_validate() untouched; verified it fails\nagainst the pre-fix model shape.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* test: cover JSON-output authority for an AG rule (#153)\n\nThe only existing test of this shape, test_cli_json_output_includes_authority,\nexercised FM010. #132's checklist named JSON/text reporters as in\nscope for the AG series, and nothing exercised it. Added the same\nvalidate_file() + _assert_authority() pattern against AG001's mcp__*\ncase.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* fix: AgentFrontmatter.skills no longer hard-fails on non-JSON YAML scalars\n\nCode review on #185 found a real regression: retyping skills from\nobject | None to JsonValue made Pydantic reject any value JSON can't\nrepresent (e.g. an unquoted date-like scalar, which ruamel.yaml\nresolves to datetime.date). Reproduced end-to-end: validated cleanly\non main, raised pydantic.ValidationError here, surfaced as a confusing\nFM005 alongside AG003's pre-existing, correct warning --\nnormalize_agent_skills_value already classifies any non-str/non-list\nvalue as unsupported.\n\nWrapped the field in SkipValidation[JsonValue]: keeps JsonValue as the\nprecise static annotation (the TYPING_POLICY ask #149 was answering)\nwhile restoring the original \"accept whatever YAML produced\" runtime\nbehavior. SkipValidation alone reintroduced a different problem --\nPydantic's serializer warns on model_dump() whenever the runtime value\ndoesn't match the declared schema, exactly the case SkipValidation\nexists to accept. A field_serializer that returns the value unchanged,\ntyped object rather than JsonValue, avoids that (verified with\nwarnings-as-errors): a JsonValue-typed return re-triggers the same\nschema mismatch on the way out that SkipValidation bypassed on the way\nin.\n\nVerified via the real check pipeline: a SKILL.md-style agent file with\nskills: 2024-01-01 now produces exactly one finding (AG003), not two.\nAdded a regression test with warnings-as-errors covering both the\nvalidation and the dump path.\n\nAlso fixed three doc/comment accuracy findings from the same review:\nfrontmatter_core.py's stale claim that hk_series.py uses JsonValue \"the\nsame way\" (it's TYPE_CHECKING-only, never a live model field, so it\nnever exercises the schema-building path this fix is about);\nplugin_validator.py's now-false \"both models expose runtime-friendly\nviews of skills\" (only AgentFrontmatter does, post-#151);\nag_series.py's two AG001 suggestion strings that had drifted apart in\nwording, and an off-by-one line citation.\n\nA fourth review finding (--fix reorders an authored `skills:` key to\nthe end of the frontmatter block when it also fixes another field) is\nnot fixed here: verified it is pre-existing Pydantic extra=\"allow\" dump\nordering behavior, reproducible on main today for any already-unrecognized\nfrontmatter key -- #151 made `skills` fall into that existing category\nrather than introducing new behavior. Fixing it generally is a separate,\nlarger change (preserving original key order for every extra field, not\none field), out of scope here.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-04T06:16:15Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/bcdfd3222784940eec91154e4860f1884b968a1a"
        },
        "date": 1788502743758,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11157.611,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11738.099,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12861.985,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.278,
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
          "id": "7d69a4f0eaf8d9b82a41de7cfc30b2cf3ff13082",
          "message": "feat(provenance): scheduled L3 drift check for vendor-backed claims (#187)\n\n* fix(HK002): add PreModelSwitch and PostModelSwitch events\n\nFound live by scripts/refresh_claim_values.py (this PR's own drift\nmechanism) against a fresh capture of code.claude.com/docs/en/hooks.md\n(2026-09-04): upstream added two events since the 2026-08-28 snapshot\nPR #183 (this session, six days earlier) verified against. Strict\naddition, no removals -- same pattern as PR #183.\n\nA plugin registering either event got a false HK002 error until this\nfix.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* feat(provenance): scheduled L3 drift check for vendor-backed claims (#112)\n\nImplements Stage 4 (\"Compare\") of docs/design-rule-provenance-registry.md\nfor the two claims that currently cite a real external vendor document\n(HK002.valid_event_types, HK003.valid_hook_types) -- the other three\nclaims cite in-repo tracked schema files, already covered by every\ncommit's L2 locator+value test.\n\nscripts/refresh_claim_values.py fetches code.claude.com/docs/en/hooks.md\nfresh, re-extracts each known claim (HK002: level-3 headings under\n\"Hook events\"; HK003: the \"Common fields\" table's `type` row -- both\nmechanical, no LLM), and rewrites provenance-registry.json's\nexpected_value + x-audited in place when the live doc disagrees.\nLLM-based extraction (the design doc's Stage 3) is deliberately not\nbuilt: these two claims extract correctly without it, and nothing yet\nneeds prose interpretation.\n\n.github/workflows/claim-drift.yml runs the script weekly (+\nworkflow_dispatch), caching .claude/vendor/sources for resilience\nagainst a transient fetch failure mid-run (the script always\nforce-fetches, so the cache is not a performance optimization -- see\nits comment). Exit code 2 (no cache and fetch failed) fails the job\noutright, never silently skips -- the failure mode #155 is filed\nagainst. Exit code 1 (drift found and written) hands off to\nscripts/open_drift_pr.sh, which commits, pushes to a fixed bot-owned\nbranch, and opens a PR only the first time (a later run's push updates\nthe same open PR automatically). Uses gh directly rather than a new\nthird-party Action, since gh is already this repo's established tool\nfor this class of task.\n\nVerified live: the script found real drift while being developed\n(PreModelSwitch/PostModelSwitch, fixed in the preceding commit) and,\nseparately, its idempotent re-run and its full commit+push+PR-open\npath via open_drift_pr.sh -- the latter run created and then closed\nPR #186 when it unexpectedly found the preceding commit's changes\nstill uncommitted in the working tree during local testing.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n* fix: harden the claim-drift CI mechanism (5 review findings)\n\nCode review on #187 found five real issues:\n\n- open_drift_pr.sh's bare `git push --force-with-lease` fails with\n  \"stale info\" on every run after the branch's first push -- CI's\n  checkout never fetches chore/claim-drift-auto, so there's no\n  remote-tracking ref to compare against, even though nothing raced\n  it. Fixed by looking up the branch's real current SHA via\n  `git ls-remote` and passing it explicitly as the lease.\n- refresh_claim_values.py's main() only rewrites the registry at the\n  very end; an unhandled exception earlier (malformed JSON, a doc\n  structure an extractor can't parse) exited 1 by Python's default --\n  indistinguishable from the intentional \"drift found and written\"\n  signal, and left the registry unchanged, so open_drift_pr.sh saw\n  nothing to commit and exited 0. A crash would go green. Gave\n  unexpected errors their own exit code (3).\n- HK002 and HK003 cite the identical authority_url, but the per-claim\n  loop fetched it live once per claim -- two redundant network fetches\n  and two redundant timestamped cache files every run. Memoized the\n  fetch per URL within a single run.\n- claim-drift.yml embedded multi-line shell control flow (set +e, run\n  the script, capture $? into GITHUB_OUTPUT) directly in the workflow\n  YAML, violating AGENTS.md's \"logic belongs in scripts/, not inline\n  in YAML\" -- and set +e is load-bearing here (GH Actions runs `bash\n  -e` by default), so this wasn't cosmetic. Moved to\n  scripts/run_claim_refresh.sh and scripts/fail_claim_refresh.sh.\n- json.dumps(..., indent=2) defaults to ensure_ascii=True, so writing\n  drift for one claim re-escaped non-ASCII characters (an em dash)\n  across the whole registry file and reformatted unrelated arrays --\n  noise in every future drift PR's diff. Added ensure_ascii=False.\n\nVerified independently: the memoization fix produces exactly one new\nvendor cache file per run (was two); a malformed registry now exits 3,\nnot 1; full prek + pytest gate green.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01XATWGbELHG23qfNfvJVbDk\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-04T06:37:14Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/7d69a4f0eaf8d9b82a41de7cfc30b2cf3ff13082"
        },
        "date": 1788504008961,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 6879.704,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 7398.312,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 8400.952,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 135.301,
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
          "id": "47870cecbdd54e69956caf2afd929c5f82ea4a80",
          "message": "refactor(rule-registry): constrain category/platforms to Literal types (#190)\n\n* refactor(rule-registry): constrain category/platforms to Literal types\n\nRuleEntry.category and .platforms were plain str/list[str], so a typo'd\ncategory (e.g. \"skils\") would silently register and a typo'd\n`skilllint rules --category` CLI filter would silently return an empty\ntable instead of erroring. Add RuleCategory/RulePlatform Literal aliases\nin rules/_constants.py, sourced from grepping the 51 live\n@skilllint_rule(...) call sites, and use them on RuleEntry and the\nskilllint_rule decorator so Pydantic validates every registration at\nimport time. Validate the CLI --category option against the same\nLiteral and raise typer.BadParameter on an unknown value.\n\nCloses part of #41 (item 3).\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\n* refactor(rule-registry): type all three rules-cmd filters as Literals\n\n--category was hand-validated with a manual typer.BadParameter check\nwhile --platform and --severity, sharing the identical bug class,\nsilently accepted typos. Typing all three options as their real\nLiteral types lets Typer validate natively and removes the hand-rolled\ncheck.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-05T01:23:33Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/47870cecbdd54e69956caf2afd929c5f82ea4a80"
        },
        "date": 1788571607146,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11232.282,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11710.451,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12641.175,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.479,
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
          "id": "59d7e3c3cee0eac611b3a8d0ef130d8bb80f5d00",
          "message": "fix(LK001,NR001,PR002,PR004,SL001,PD002): reclassify opinions, fix PD002 spec citation (#196)\n\n* fix(LK001,NR001,PR002,PR004,SL001,PD002): reclassify opinions, fix PD002 spec citation\n\nFive rules cited a personal repo (github.com/jamie-bitflight/claude_skills)\nas authority with no real content behind it. A research pass this session\nfound no vendor doc traceable source for any of them; a human reviewed and\napproved reclassifying them as skilllint's own lint opinions:\n\n- LK001: broken internal markdown link — no vendor doc requires links resolve\n- NR001: namespace reference target existence — not documented upstream\n- PR002: registered capability path existence — not documented upstream\n- PR004: plugin.json repository field vs git remote match — not documented\n- SL001: symlink target trailing-whitespace check — not documented\n\nEach now carries an inline \"No authority: ...\" comment instead of the\nauthority field, matching the house style already used in sk_series.py and\nhk_series.py. No opinion-catalog.json entries were added: none of the five\nrules has a genuine pre-existing named constant capturing its check (only\nLK001, NR001, and PR002/004 use inline regexes or plain existence checks),\nso inventing one purely to satisfy the catalog schema was rejected per the\nHK004 precedent.\n\nPD002 is a real behavior change, not just a citation fix: research found the\nagentskills.io spec documents `assets/` (templates, images, data files) as\nthe third optional progressive-disclosure directory alongside `references/`\nand `scripts/` — it never mentions `examples/`. PD002 now checks for\n`assets/` instead, with authority pointing at the spec's `assets` anchor\n(confirmed via `skilllint docs fetch` + `docs sections`). Any skill with an\n`examples/` directory but no `assets/` directory will now be flagged where\nit previously was not, and vice versa — updated the one test assertion and\n19 fixture skill directories (renamed `examples/` to `assets/`) that relied\non the old directory name to stay silent under PD002.\n\nRef #40\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\n* fix(PD002): correct stale examples/ banner comment to assets/\n\nThe section-banner comment still read \"No examples/ directory found\"\nafter the check was changed to look for assets/, contradicting the\ndocstring and behavior three lines below it.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\n---------\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-05T01:31:12Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/59d7e3c3cee0eac611b3a8d0ef130d8bb80f5d00"
        },
        "date": 1788572042710,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11046.521,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11626.107,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12761.468,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 86.099,
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
          "id": "c16c62b28cdff642fd384c4e1379807e3080bc8a",
          "message": "fix(PR001,PR003,TC001): final 3 rules of the #40 authority-origin sweep (#198)\n\nPR001 and PR003 get real code.claude.com citations (plugins-reference.md's\n\"Path behavior rules\" and \"Metadata fields\" sections respectively, verified\nvia `skilllint docs fetch`), replacing the placeholder personal-repo origin.\nTC001 is a pure measurement/telemetry rule with no pass/fail semantics or\nthreshold — its authority is removed entirely and replaced with a one-line\ncomment, matching the precedent set for other no-authority rules; no\nopinion-catalog.json entry was added since TC001 has no underlying constant\nto anchor one to.\n\nPR005 is deliberately left untouched (tracked separately by #195), and the\npre-existing PluginRegistrationValidator wiring gap is out of scope.\n\n\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-05T01:38:59Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/c16c62b28cdff642fd384c4e1379807e3080bc8a"
        },
        "date": 1788572501065,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11044.587,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11754.083,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12930.099,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.162,
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
          "id": "4fbfd1f400ba4e6a10710d481c386c90f31f9dda",
          "message": "fix(PD001,PD003): cite real agentskills.io spec authority (#197)\n\nReplaces the bogus github.com/jamie-bitflight/claude_skills authority\non PD001 (references/) and PD003 (scripts/) with the real\nagentskills.io/specification.md citations, verified by fetching the\nspec via `skilllint docs fetch`. Completes PD-series authority\ncoverage alongside #196, which fixes PD002 separately.\n\n\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-05T01:46:18Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/4fbfd1f400ba4e6a10710d481c386c90f31f9dda"
        },
        "date": 1788572939530,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11017.761,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11617.874,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12710.003,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 86.16,
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
          "id": "3d77807dfde65fd246a54b5fee0fbaab675fe548",
          "message": "fix(PR001): suppress default-discovery false positives for agents/commands (#208)\n\nInvestigating issue #200 (PR001's skills-array suppression) against the\nfreshly re-fetched code.claude.com/docs/en/plugins-reference.md#path-behavior-rules\nfound that the issue's own diagnosis of the current code does not hold: a\nrunnable check against `check_pr001` shows declaring an explicit `skills`\narray (even empty) does NOT suppress PR001 today -- it already warns in\nthat case, and only suppresses when `skills` is absent entirely. That is\nthe doc-correct behavior (skills is additive; ./skills/ is always scanned\nregardless of declaration), so no change was needed there beyond dropping a\ndead, confusing path-check clause the original condition carried\n(`actual_skills` can only ever contain \"skills/\"-prefixed paths, so\n`not str(orphan).startswith(\"skills/\")` never evaluated true) and correcting\nthe docstring's inaccurate blanket claim that any explicit array replaces\ndefault discovery.\n\nThe same doc section confirmed a real, mirror-image bug: `agents` and\n`commands` DO replace default discovery once declared, but check_pr001 had\nno suppression at all for them, so a plugin with no `agents`/`commands` key\n(fully auto-discovered, same as an unregistered `skills` array) got PR001\nfalse positives for every agent/command file on disk. Added the same\n\"suppressed while absent, warned once declared\" gate already used for\nskills (and already precedented by the SK009 check in plugin_validator.py).\n\nAdded regression tests: an explicit-empty-array-must-still-warn guard for\nskills (protecting against a naive fix that would silently disable the\ncheck by always evaluating the dead path-check clause to False), plus new\nabsent/declared coverage for agents and commands.\n\n\nClaude-Session: https://claude.ai/code/session_01G3ke4pBmhpiEuWoFTV2ax4\n\nCo-authored-by: Claude Sonnet 5 <noreply@anthropic.com>",
          "timestamp": "2026-09-06T05:54:38Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/3d77807dfde65fd246a54b5fee0fbaab675fe548"
        },
        "date": 1788674237570,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 11033.041,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 11674.129,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 12847.902,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 85.745,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}