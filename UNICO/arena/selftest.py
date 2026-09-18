import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ROOT / "arena_agent.py",
    ROOT / "arena_reconcile.py",
]
FORBIDDEN = ("ca.lane_score = adaptive_lane_score", "ca.create_bids = adaptive_create_bids", "recursive")

for path in FILES:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

agent = (ROOT / "arena_agent.py").read_text(encoding="utf-8")
for marker in FORBIDDEN:
    assert marker not in agent, f"forbidden architecture marker: {marker}"

print("ARENA_SELFTEST_OK")
