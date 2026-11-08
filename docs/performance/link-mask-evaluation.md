# Link-mask optimization evidence

The product change replaces each maximal non-newline run with an equal-length
run of spaces during link extraction. It avoids one regex replacement per
character while preserving Python character offsets, CR/LF positions and
existing link parsing. There are no new product dependencies or public APIs.

## Observed performance

The November 7, 2026 experiments compared baseline
`85813670fbaf8755cc81698497b992cb0a1d2b60` with product change
`41a53b7a7b00e236f2f2f8fc076dbaa965bf2ac8`. These are historical measurements,
not new measurements of the later test/documentation cleanup.

- On a pinned private 447-file projection, median paired candidate/baseline
  ratios were 0.91544 for default check, 0.94455 for JSON check and 0.96291 for
  no-op fix. This supports a modest improvement on that workload only.
- Short checks and synthetic modifying fix showed no dependable benefit.
  A ten-file row was 1.04864; a separate 30-pair repeat was 0.99057. The initial
  slowdown did not reproduce at that magnitude, but equivalence is not proved.
- On a complete public community corpus, default/JSON/fix ratios were
  0.98189/0.98305/0.96976. Every interquartile range crossed 1, so these runs
  do not establish a consistent broad speedup.
- Actual staged-hook sessions gave 1.05224 initially and 0.97182 in a separate
  30-pair repeat. Variability was substantial. Neither a dependable hook
  speedup nor performance equivalence is established.
- Import behavior remains a caveat. A separate controlled wheel session gave
  paired medians of 0.99685 for package import and 1.02084 for rules import,
  while CI reported much larger mean increases. That experiment did not
  establish CI noise, equivalent environments or the absence of a startup cost.

Ratios below 1 favor the candidate. Runs alternated endpoints, excluded declared
warmups and required exact output, exit and final-file parity. Ordinary rows
used ten measured pairs. Sessions were not pooled. The private corpus omitted
22 PNGs and one large graph JSON; missing assets may affect findings. The staged
corpus retained all source paths on disk but omitted 14 ignored upstream paths
from its reconstructed index. One Linux host and Python version were measured;
OS caches, CPU behavior and external contention were uncontrolled. No universal
speedup or statistical-equivalence claim is made.

## Preserved research

The temporary evaluation runners, their tests and raw exports are not part of
the maintained product change. Their original bytes and detailed limitations
remain available at immutable commit
[`7f5dc12`](https://github.com/bitflight-devops/skilllint/commit/7f5dc12f7e9fbf678d4abbf4e2eabb5a9ed95741):

- [Primary workloads and adjacent raw samples](https://github.com/bitflight-devops/skilllint/tree/7f5dc12f7e9fbf678d4abbf4e2eabb5a9ed95741/docs/performance/primary-paired-2026-11-07)
- [Independent corpus and ten-file repeat](https://github.com/bitflight-devops/skilllint/tree/7f5dc12f7e9fbf678d4abbf4e2eabb5a9ed95741/docs/performance/secondary-paired-2026-11-07)
- [Actual staged workflow and repeat](https://github.com/bitflight-devops/skilllint/tree/7f5dc12f7e9fbf678d4abbf4e2eabb5a9ed95741/docs/performance/staged-hook-2026-11-07)
- [Import diagnostic](https://github.com/bitflight-devops/skilllint/tree/7f5dc12f7e9fbf678d4abbf4e2eabb5a9ed95741/docs/performance/import-diagnostic-2026-11-07)

These links preserve the evidence without adding a reusable benchmarking system
to the repository's current maintenance surface. Private source and raw findings
were not published; only reviewed, allowlisted exports are in those records.
