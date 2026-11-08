"""Keep the public gallery linked to real report artifacts."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples/output"
FORMATS = [
    ("full", "full.ansi"),
    ("concise", "concise.txt"),
    ("json-lines", "json-lines.jsonl"),
    ("github", "github.txt"),
    ("gitlab", "gitlab.json"),
    ("junit", "junit.xml"),
]


@pytest.mark.parametrize(("name", "raw_name"), FORMATS)
def test_gallery_links_real_reports_and_complete_svg(name, raw_name):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    gallery = (OUTPUT / "README.md").read_text(encoding="utf-8")
    assert f"examples/output/{name}.svg" in readme
    assert f"examples/output/{raw_name}" in readme
    assert f"]({name}.svg)" in gallery
    assert f"]({raw_name})" in gallery
    assert (OUTPUT / raw_name).read_bytes()
    root = ET.fromstring((OUTPUT / f"{name}.svg").read_bytes())
    ids = {node.attrib["id"] for node in root.iter() if "id" in node.attrib}
    for node in root.iter("{http://www.w3.org/2000/svg}text"):
        clip = node.attrib.get("clip-path")
        if clip and (node.text or "").strip():
            assert clip.startswith("url(#")
            assert clip.endswith(")")
            assert clip[5:-1] in ids
    assert "FM010" in "".join(root.itertext())
