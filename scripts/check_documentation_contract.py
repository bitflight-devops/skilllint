"""Check the repository's maintained documentation contract."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import urldefrag, urlparse

from readme_renderer.markdown import render

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git") or "git"
EXPECTED = {
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/TYPING_POLICY.md",
    "docs/design-markdown-link-conventions.md",
    "docs/design-rule-provenance-registry.md",
    "docs/maintainer-extension-guide.md",
    "docs/runtime-contracts/claude-code-agent-skills-2.1.251.md",
    "docs/usage.md",
    "docs/vendor-cache.md",
    "docs/architecture.md",
    "plugins/agentskills-skilllint/README.md",
    "plugins/agentskills-skilllint/skills/skilllint/SKILL.md",
}
LINK = re.compile(r"!?(?:\[[^]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")
FENCE = re.compile(r"^```.*?^```\s*$", re.MULTILINE | re.DOTALL)


def _tracked() -> set[str]:
    result = subprocess.run([GIT, "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True)
    return set(result.stdout.splitlines())


def _narrative(tracked: set[str]) -> set[str]:
    return {
        p
        for p in tracked
        if p in {"AGENTS.md", "CLAUDE.md", "README.md"}
        or (p.startswith("docs/") and p.endswith(".md"))
        or p in {"plugins/agentskills-skilllint/README.md", "plugins/agentskills-skilllint/skills/skilllint/SKILL.md"}
    }


def _validate_links(path: str, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    for raw in LINK.findall(FENCE.sub("", text)):
        if raw == "url" or any(token in raw for token in ("*", "[", "]", "{", "}")):
            continue
        if urlparse(raw).scheme in {"http", "https", "mailto"}:
            continue
        link, anchor = urldefrag(raw)
        destination = (root / path).resolve() if not link else (root / path).parent.joinpath(link).resolve()
        if not destination.is_file() or not destination.is_relative_to(root.resolve()):
            errors.append(f"{path}: missing link {raw}")
        elif anchor:
            headings = {
                re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
                for h in re.findall(r"^#{1,6} +(.+)$", destination.read_text(encoding="utf-8"), re.MULTILINE)
            }
            if anchor not in headings:
                errors.append(f"{path}: missing anchor {raw}")
    return errors


def validate_documentation_contract(root: Path = ROOT) -> list[str]:
    """Return violations in the maintained file inventory and local links."""
    errors: list[str] = []
    tracked = (
        _tracked()
        if root == ROOT
        else set(
            subprocess.run([GIT, "ls-files"], cwd=root, check=True, capture_output=True, text=True).stdout.splitlines()
        )
    )
    narrative = _narrative(tracked)
    ownership_path = root / "docs/documentation-ownership.toml"
    try:
        owners = tomllib.loads(ownership_path.read_text(encoding="utf-8"))["owners"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        return [f"cannot load ownership: {exc}"]
    if narrative != EXPECTED:
        errors.append(
            f"narrative inventory mismatch: extra={sorted(narrative - EXPECTED)} missing={sorted(EXPECTED - narrative)}"
        )
    if set(owners) != EXPECTED:
        errors.append("ownership mapping must contain exactly the 13 maintained files")
    values = list(owners.values())
    if len(values) != len(set(values)):
        errors.append("ownership topics must be unique")
    for path in EXPECTED:
        target = root / path
        if not target.is_file():
            errors.append(f"missing maintained document: {path}")
            continue
        errors.extend(_validate_links(path, target.read_text(encoding="utf-8"), root))
    return errors


def _artifact_readmes(directory: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for artifact in (*directory.glob("*.whl"), *directory.glob("*.tar.gz")):
        if artifact.suffix == ".whl":
            with zipfile.ZipFile(artifact) as archive:
                names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
                metadata = archive.read(names[0]).decode() if names else ""
        else:
            with tarfile.open(artifact) as archive:
                member = next((m for m in archive.getmembers() if m.name.endswith("/PKG-INFO")), None)
                stream = archive.extractfile(member) if member else None
                metadata = stream.read().decode() if stream else ""
        description = metadata.split("\n\n", 1)[1] if "\n\n" in metadata else ""
        result[artifact.name] = description.rstrip() + "\n"
    return result


def _artifact_results(directory: Path) -> tuple[dict[str, object], list[str]]:
    expected = (ROOT / "README.md").read_text(encoding="utf-8")
    results: dict[str, object] = {"artifacts": {}}
    errors: list[str] = []
    for name, description in _artifact_readmes(directory).items():
        match = description == expected
        rendered = render(description) is not None
        results["artifacts"][name] = {"long_description_matches": match, "rendered": rendered}
        if not match:
            errors.append(f"{name}: long description differs from README.md")
        if not rendered:
            errors.append(f"{name}: long description does not render")
    if not results["artifacts"]:
        errors.append("no wheel or sdist artifacts found")
    return results, errors


def main() -> int:
    """Run the contract checker and optional evidence modes.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-json", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--render-json", type=Path)
    args = parser.parse_args()
    errors = validate_documentation_contract()
    if args.external_json:
        links: list[dict[str, str]] = []
        for path in EXPECTED:
            text = (ROOT / path).read_text(encoding="utf-8")
            links.extend(
                {"url": raw, "source": path, "status": "unverified"}
                for raw in LINK.findall(text)
                if urlparse(raw).scheme in {"http", "https"}
            )
        args.external_json.write_text(json.dumps({"links": links}, indent=2) + "\n", encoding="utf-8")
    if args.artifacts or args.render_json:
        if not args.artifacts or not args.render_json:
            errors.append("--artifacts and --render-json must be provided together")
        else:
            artifact_results, artifact_errors = _artifact_results(args.artifacts)
            errors.extend(artifact_errors)
            args.render_json.write_text(json.dumps(artifact_results, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
