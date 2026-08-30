// scripts/post_coverage_summary.test.mjs
// Run: node --test scripts/post_coverage_summary.test.mjs

import { strict as assert } from 'node:assert';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, it } from 'node:test';

import postCoverageSummary from './post_coverage_summary.mjs';

function mockGithub() {
  // ponytail: mutable holder object, not closures that reassign local vars
  const state = { updated: null, created: null, comments: [] };

  return {
    rest: {
      issues: {
        listComments: async () => ({ data: state.comments }),
        updateComment: async (params) => {
          state.updated = params;
          return { status: 200 };
        },
        createComment: async (params) => {
          state.created = params;
          return { status: 201 };
        },
      },
    },
    _state: state,
  };
}

function mockContext() {
  return {
    repo: { owner: 'bitflight-devops', repo: 'skilllint' },
    issue: { number: 42 },
  };
}

function withTempCoverageDir(testFn) {
  return async () => {
    const dir = mkdtempSync(join(tmpdir(), 'cov-'));
    mkdirSync(join(dir, 'coverage-reports'), { recursive: true });
    const origCwd = process.cwd();
    process.chdir(dir);
    try {
      await testFn(dir);
    } finally {
      process.chdir(origCwd);
      rmSync(dir, { recursive: true, force: true });
    }
  };
}

describe('postCoverageSummary', () => {
  it(
    'creates comment when none exists (line-rate 0.85 → 85.00%)',
    withTempCoverageDir(async () => {
      writeFileSync(
        'coverage-reports/coverage.xml',
        `<coverage line-rate="0.85" branch-rate="0.7"/>`,
      );

      const gh = mockGithub();
      await postCoverageSummary({ github: gh, context: mockContext() });

      assert.equal(
        gh._state.created.body,
        '## 📊 Test Coverage Report\n\n**Coverage:** 85.00%\n\n📥 Coverage XML available as artifact: `coverage-xml`',
      );
      assert.equal(gh._state.updated, null);
    }),
  );

  it(
    'updates existing sticky comment (preserves first-match predicate)',
    withTempCoverageDir(async () => {
      writeFileSync('coverage-reports/coverage.xml', `<coverage line-rate="1.0"/>`);

      const gh = mockGithub();
      gh._state.comments.push({
        id: 999,
        user: { type: 'Bot' },
        body: '## 📊 Test Coverage Report\n\n**Coverage:** 50.00%\n\n...',
      });

      await postCoverageSummary({ github: gh, context: mockContext() });

      assert.equal(gh._state.updated.comment_id, 999);
      assert.equal(gh._state.created, null);
    }),
  );

  it(
    'returns N/A when line-rate attribute missing',
    withTempCoverageDir(async () => {
      writeFileSync('coverage-reports/coverage.xml', `<coverage branch-rate="0.5"/>`);

      const gh = mockGithub();
      await postCoverageSummary({ github: gh, context: mockContext() });

      assert.ok(gh._state.created.body.includes('N/A'));
    }),
  );
});
