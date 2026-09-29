"""Run the skilllint CLI with ``python -m skilllint``."""

from __future__ import annotations

from skilllint.plugin_validator import app

if __name__ == "__main__":
    app(prog_name="skilllint")
