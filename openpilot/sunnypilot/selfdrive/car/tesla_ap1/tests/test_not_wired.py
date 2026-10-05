"""The AP1 package must not be imported by the live car stack in this repo."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
NEEDLE = "tesla_ap1"


def test_live_tree_does_not_import_tesla_ap1():
  roots = [
    ROOT / "openpilot/selfdrive",
    ROOT / "openpilot/sunnypilot",
  ]
  hits = []
  package = ROOT / "openpilot/sunnypilot/selfdrive/car/tesla_ap1"
  for base in roots:
    for path in base.rglob("*"):
      if not path.is_file() or path.suffix not in {".py", ".cc", ".h", ".pyx"}:
        continue
      if package in path.parents or path == package:
        continue
      text = path.read_text(errors="replace")
      if NEEDLE in text:
        hits.append(str(path.relative_to(ROOT)))
  assert hits == []
