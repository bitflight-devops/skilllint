"""Rule-set constants for the skilllint rules package."""

from __future__ import annotations

# 14 series: AS + FM + PA (existing 3) + SK + LK + PD + PL + HK + NR + SL + TC + PR
# (9 extracted from monolith) + CU + CX (2 adapter-backed). CM001 is scoped out.
MIN_REGISTERED_SERIES: int = 14
