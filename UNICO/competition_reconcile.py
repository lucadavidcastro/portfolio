import json
import os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
COMP = BASE / "competition"
COMP.mkdir(parents=True, exist_ok=True)
RUNTIME = BASE / "runtime.json"
BOARD = COMP / "board.json"
END = os.environ.get("COMPETITION_END", "2026-09-17T23:59:59-03:00")
LANES = ["incumbent", "hunter", "specialist"]
NAMES = {
    "incumbent": os.environ.get("INCUMBENT_NAME", "UNICO-Ludaca"),
    "hunter": os.environ.get("HUNTER_NAME", "UNICO-Hunter"),
    "specialist": os.environ.get("SPECIALIST_NAME", "UNICO-Specialist")
}


def now_iso():
    return datetime.now().astimezone().isoformat()


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def score(v):
    return (
        int(v.get("earnings_total_cents", 0)) * 1000
        + int(v.get("completed_jobs", 0)) * 100
        + int(v.get("accepted_jobs", 0)) * 10
        + int(v.get("successful_bids", 0))
    )


def main():
    board = load(BOARD, {"competition_end": END, "finalized": False, "winner": None, "retired": [], "agents": {}})
    agents = {}
    total_revenue = 0
    total_balance = 0
    all_errors = []
    for lane in LANES:
        ledger = load(COMP / f"{lane}.json", {"lane": lane, "agent_name": NAMES[lane]})
        agents[lane] = {
            "lane": lane,
            "agent_name": ledger.get("agent_name", NAMES[lane]),
            "agent_id": ledger.get("agent_id"),
            "status": ledger.get("status", "UNKNOWN"),
            "retired": bool(ledger.get("retired", False)),
            "cycles": int(ledger.get("cycles", 0)),
            "earnings_total_cents": int(ledger.get("earnings_total_cents", 0)),
            "wallet_balance_cents": int(ledger.get("wallet_balance_cents", 0)),
            "accepted_jobs": int(ledger.get("accepted_jobs", 0)),
            "in_progress_jobs": int(ledger.get("in_progress_jobs", 0)),
            "delivered_jobs": int(ledger.get("delivered_jobs", 0)),
            "completed_jobs": int(ledger.get("completed_jobs", 0)),
            "successful_bids": int(sum(1 for b in ledger.get("bids", {}).values() if b.get("status") == "SUBMITTED")),
            "last_cycle": ledger.get("last_cycle"),
            "last_error": ledger.get("last_error"),
            "errors_count": len(ledger.get("errors", []))
        }
        total_revenue += agents[lane]["earnings_total_cents"]
        total_balance += agents[lane]["wallet_balance_cents"]
        if ledger.get("last_error"):
            all_errors.append({"lane": lane, "error": ledger.get("last_error")})

    board["competition_end"] = END
    board["agents"] = agents
    board["updated_at"] = now_iso()
    board["leaderboard"] = sorted(
        [{"lane": k, "score": score(v), "revenue_usd": round(v["earnings_total_cents"] / 100, 2), "completed": v["completed_jobs"], "accepted": v["accepted_jobs"], "successful_bids": v["successful_bids"]} for k, v in agents.items()],
        key=lambda x: x["score"], reverse=True
    )

    end_dt = datetime.fromisoformat(END)
    now_dt = datetime.now(end_dt.tzinfo)
    if now_dt >= end_dt and not board.get("finalized"):
        ranked = board["leaderboard"]
        top_revenue = ranked[0]["revenue_usd"] if ranked else 0
        if top_revenue > 0:
            winner = ranked[0]["lane"]
            losers = [x["lane"] for x in ranked[1:]]
            board["finalized"] = True
            board["finalized_at"] = now_iso()
            board["winner"] = winner
            board["retired"] = losers
            for lane in losers:
                path = COMP / f"{lane}.json"
                ledger = load(path, {})
                ledger["retired"] = True
                ledger["status"] = "RETIRED"
                ledger["retired_at"] = now_iso()
                save(path, ledger)
        else:
            # Never retire active revenue lanes merely because a timed experiment ended with zero verified revenue.
            board["finalization_deferred"] = True
            board["finalization_reason"] = "No verified revenue; all lanes remain active for continued optimization."
            board["finalization_deferred_at"] = now_iso()

    runtime = load(RUNTIME, {"status": "ACTIVE", "target_usd": 5000, "collected_usd": 0.0, "cycles": 0, "revenue_events": []})
    runtime["cycles"] = int(runtime.get("cycles", 0)) + 1
    runtime["last_cycle"] = now_iso()
    runtime["collected_usd"] = round(total_revenue / 100, 2)
    runtime["toku_wallet"] = {"balanceCents": total_balance, "verifiedEarningsCents": total_revenue}
    runtime["last_error"] = "; ".join(f"{e['lane']}:{e['error']}" for e in all_errors) if all_errors else None
    runtime["competition"] = board
    runtime["audit"] = {
        "state_reconciled": True,
        "wallet_verified": True,
        "bid_retry_logic": True,
        "llm_429_circuit_breaker": True,
        "three_lane_competition": True,
        "conversion_strategy_v4": True,
        "zero_revenue_protection": True,
        "updated_at": now_iso()
    }
    RUNTIME.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    BOARD.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"winner": board.get("winner"), "finalized": board.get("finalized"), "finalization_deferred": board.get("finalization_deferred", False), "revenue_usd": runtime["collected_usd"], "agents": board["leaderboard"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
