import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
COMP = BASE / "competition"
STRATEGY = BASE / "strategy.json"
AUDIT = BASE / "AUDIT.md"

DEFAULTS = {
    "incumbent": {"min_budget": 150, "max_bids": 14, "base_ratio": 0.18, "high_bid_cutoff": 75},
    "hunter": {"min_budget": 150, "max_bids": 16, "base_ratio": 0.16, "high_bid_cutoff": 75},
    "specialist": {"min_budget": 300, "max_bids": 12, "base_ratio": 0.22, "high_bid_cutoff": 75},
}


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def now_dt():
    return datetime.now(timezone.utc)


def now():
    return now_dt().isoformat()


def main():
    strategy = load(STRATEGY, {"version": "v4", "lanes": DEFAULTS, "global": {}})
    last = strategy.get("updated_at")
    if last:
        try:
            elapsed = (now_dt() - datetime.fromisoformat(last).astimezone(timezone.utc)).total_seconds()
            if elapsed < 1800:
                print(json.dumps({"updated": False, "skipped": True, "reason": f"30m gate; only {int(elapsed)}s elapsed"}))
                return
        except Exception:
            pass

    board = load(COMP / "board.json", {"agents": {}})
    lanes = strategy.setdefault("lanes", {})
    changes = []
    total_bids = 0
    total_revenue = 0.0

    for lane, defaults in DEFAULTS.items():
        state = dict(defaults)
        state.update(lanes.get(lane, {}))
        agent = board.get("agents", {}).get(lane, {})
        bids = int(agent.get("successful_bids", 0))
        accepted = int(agent.get("accepted_jobs", 0))
        completed = int(agent.get("completed_jobs", 0))
        revenue = float(agent.get("earnings_total_cents", 0)) / 100.0
        total_bids += bids
        total_revenue += revenue

        if bids >= 20 and accepted == 0:
            old_ratio = float(state["base_ratio"])
            old_cutoff = int(state["high_bid_cutoff"])
            state["base_ratio"] = max(0.08, round(old_ratio * 0.82, 4))
            state["high_bid_cutoff"] = max(40, old_cutoff - 10)
            changes.append(f"{lane}: zero acceptance after {bids} bids -> ratio {old_ratio:.4f}->{state['base_ratio']:.4f}; crowded-job cutoff {old_cutoff}->{state['high_bid_cutoff']}")
        elif accepted > 0 and completed == 0:
            changes.append(f"{lane}: acceptance detected ({accepted}/{bids}) but no completed job yet -> hold pricing")
        elif completed > 0 and revenue > 0:
            old_ratio = float(state["base_ratio"])
            state["base_ratio"] = min(0.35, round(old_ratio * 1.08, 4))
            changes.append(f"{lane}: verified completion/revenue -> ratio {old_ratio:.4f}->{state['base_ratio']:.4f}")
        elif bids < 20:
            changes.append(f"{lane}: insufficient conversion sample ({bids} bids) -> hold")

        lanes[lane] = state

    strategy["version"] = "v4-adaptive"
    strategy["updated_at"] = now()
    strategy["global"] = {
        "total_bids": total_bids,
        "verified_revenue_usd": round(total_revenue, 2),
        "last_reason": " | ".join(changes),
        "controller_runs": int(strategy.get("global", {}).get("controller_runs", 0)) + 1,
    }
    STRATEGY.write_text(json.dumps(strategy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    old_audit = AUDIT.read_text(encoding="utf-8") if AUDIT.exists() else "# UNICO Audit\n"
    entry = "\n\n## Adaptive controller " + now() + "\n\n" + "\n".join(f"- {c}" for c in changes) + f"\n- Aggregate bids: {total_bids}\n- Verified revenue: USD {total_revenue:.2f}\n"
    AUDIT.write_text(old_audit.rstrip() + entry + "\n", encoding="utf-8")
    print(json.dumps({"updated": True, "total_bids": total_bids, "verified_revenue_usd": round(total_revenue, 2), "changes": changes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
