#!/usr/bin/env node
// Check for vendor documentation drift at session start.
// Runs `uv run scripts/fetch_platform_docs.py` and injects context
// when drift is detected (exit code 2).

const { execFile } = require('child_process');
const path = require('path');

// Read stdin (hook context JSON) — may be empty for SessionStart
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  runDriftCheck();
});

function runDriftCheck() {
  const scriptPath = path.join(process.cwd(), 'scripts', 'fetch_platform_docs.py');

  // Locate uv binary
  let uvPath;
  try {
    const { execFileSync } = require('child_process');
    uvPath = execFileSync('which', ['uv'], { encoding: 'utf8', timeout: 5000 }).trim();
  } catch (_) {
    process.stderr.write('vendor-drift-check: warning: uv not found, skipping drift check\n');
    process.stdout.write('{}');
    return;
  }

  const child = execFile(
    uvPath,
    ['run', scriptPath],
    { timeout: 60000, cwd: process.cwd(), encoding: 'utf8' },
    (error, stdout, stderr) => {
      if (stderr) {
        process.stderr.write(stderr);
      }

      if (!error) {
        // Exit code 0: no drift detected
        process.stdout.write('{}');
        return;
      }

      const exitCode = error.code === 'ETIMEDOUT' ? -1 : (error.status ?? -1);

      if (exitCode === 2) {
        // Drift detected — inject context for the session
        const result = {
          hookSpecificOutput: {
            additionalContext:
              'Vendor documentation has changed. `.claude/vendor/.drift-pending.json` lists affected providers with diffs and changelogs. Run the schema-drift-auditor agent to assess whether schema fields are affected.'
          }
        };
        process.stdout.write(JSON.stringify(result));
        return;
      }

      // Any other exit code: log and stay silent
      process.stderr.write(
        `vendor-drift-check: fetch_platform_docs.py exited with code ${exitCode}\n`
      );
      process.stdout.write('{}');
    }
  );
}
