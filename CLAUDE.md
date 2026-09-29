# skilllint — Claude Development Notes

@AGENTS.md

This file adds Claude-specific orchestration behavior to the universal repository
contract in `AGENTS.md`.

## Orchestrator delegation discipline

Claude operates as an orchestrator — it coordinates agents rather than doing file-level work itself.

**The rule:** Do not read a source file, config, or test file into the orchestrator context merely to hand its contents to a subagent. Pass the file path and task boundary to the subagent instead. Read files directly when the current task is itself investigation, review, verification, or an edit that requires that evidence.

**Why this matters:**
- Reading files consumes shared context window space.
- Agents have fresh context and can discover, diagnose, and fix within a delegated boundary.
- The orchestrator stays lightweight when delegation is actually useful.

**For CI failures specifically:**
- Prefer delegating log fetching, root-cause analysis, and the fix as one bounded task when a suitable subagent is available.
- Verify the resulting artifact or diff before repeating the subagent's conclusions as evidence.

**For formatting/lint fixes:**
- Delegate mechanical fixes when that reduces context load, but keep the repository verification contract from `AGENTS.md` authoritative.
