// scripts/post_coverage_summary.mjs
// Extracted from .github/workflows/test.yml coverage-summary job (issue #42).
// No npm deps — stdlib only. Node 24 floor (matches actions/github-script@v9 runner).

import { readFileSync } from 'node:fs';

/**
 * Read coverage.xml, compute line-rate %, upsert a sticky PR comment.
 *
 * @param {{ github: object, context: object }} deps — injected by github-script
 */
export default async function postCoverageSummary({ github, context }) {
  const xml = readFileSync('coverage-reports/coverage.xml', 'utf8');
  const match = xml.match(/line-rate="([^"]+)"/);
  const coverage = match ? `${(parseFloat(match[1]) * 100).toFixed(2)}%` : 'N/A';

  const comments = await github.rest.issues.listComments({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
  });

  const existing = comments.data.find(
    (c) => c.user?.type === 'Bot' && c.body.includes('📊 Test Coverage'),
  );

  const body =
    `## 📊 Test Coverage Report\n\n` +
    `**Coverage:** ${coverage}\n\n` +
    `📥 Coverage XML available as artifact: \`coverage-xml\``;

  if (existing) {
    await github.rest.issues.updateComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      comment_id: existing.id,
      body,
    });
  } else {
    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: context.issue.number,
      body,
    });
  }
}
