"""skilllint rule modules.

Each series module registers its rule functions with ``@skilllint_rule``
(see ``skilllint.rule_registry.skilllint_rule`` for the decorator contract).
Signatures are not a uniform frontmatter triple: each function's parameters
state the input its rule actually reads (frontmatter dict, file content,
a filesystem path, a parsed manifest, ...), which varies by what the rule
needs to detect.

Import note: ``rules/`` functions that need ``ValidationIssue`` (and other
``plugin_validator`` symbols) import them inside the function body rather
than at module level, because ``plugin_validator`` imports ``rules/`` —
a module-level import the other way would be circular.
"""

from __future__ import annotations

from skilllint.rules import (
    ag_series as ag_series,
    as_series as as_series,
    cu_series as cu_series,
    cx_series as cx_series,
    fm_series as fm_series,
    hk_series as hk_series,
    lk_series as lk_series,
    nr_series as nr_series,
    pa_series as pa_series,
    pd_series as pd_series,
    pl_series as pl_series,
    pr_series as pr_series,
    sk_series as sk_series,
    sl_series as sl_series,
    tc_series as tc_series,
)
from skilllint.rules._constants import (
    EXPECTED_SERIES as EXPECTED_SERIES,
    MIN_REGISTERED_SERIES as MIN_REGISTERED_SERIES,
)
