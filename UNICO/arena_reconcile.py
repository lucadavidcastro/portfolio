import json, os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
ARENA = BASE / "arena"
RUNTIME = BASE / "runtime.json"
BOARD = ARENA / "board.json"
END = os.environ.get("ARENA_END", "2026-09-18T11:33:00-03:00")
TARGET = float(os.environ.get("ARENA_TARGET_USD", "100"))
LANES = ["sniper","research","creative","builder","premium"]
NAMES = {
    "sniper":"UNICO-Sniper","research":"UNICO-Research","creative":"UNICO-Creative",
    "builder":"UNICO-Builder","premium":"UNICO-Premium"
}

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\\n", encoding="utf-8")

def now_iso():
    return datetime.now().astimezone().isoformat()

def main():
    agents={}
    revenue=0
    balance=0
    errors=[]
    evaluations=0
    bids=0
    for lane in LANES:
        ledger=load(ARENA/f"{lane}.json", {"lane":lane,"agent_name":NAMES[lane]})
        earned=int(ledger.get("earnings_total_cents",0))
        bal=int(ledger.get("wallet_balance_cents",0))
        agents[lane]={
            "lane":lane,
            "agent_name":ledger.get("agent_name",NAMES[lane]),
            "agent_id":ledger.get("agent_id"),
            "status":ledger.get("status","UNKNOWN"),
            "cycles":int(ledger.get("cycles",0)),
            "candidate_evaluations":int(ledger.get("candidate_evaluations",0)),
            "bids_submitted_total":int(ledger.get("bids_submitted_total",0)),
            "accepted_jobs":int(ledger.get("accepted_jobs",0)),
            "in_progress_jobs":int(ledger.get("in_progress_jobs",0)),
            "delivered_jobs":int(ledger.get("delivered_jobs",0)),
            "completed_jobs":int(ledger.get("completed_jobs",0)),
            "earnings_total_cents":earned,
            "wallet_balance_cents":bal,
            "last_cycle":ledger.get("last_cycle"),
            "last_error":ledger.get("last_error"),
            "errors_count":len(ledger.get("errors",[]))
        }
        revenue += earned
        balance += bal
        evaluations += agents[lane]["candidate_evaluations"]
        bids += agents[lane]["bids_submitted_total"]
        if ledger.get("last_error"):
            errors.append(f"{lane}:{ledger['last_error']}")

    board=load(BOARD, {"competition_end":END,"target_usd":TARGET,"finalized":False,"retired":[]})
    board.update({
        "competition_end":END,
        "target_usd":TARGET,
        "updated_at":now_iso(),
        "agents":agents,
        "aggregate":{
            "verified_revenue_usd":round(revenue/100,2),
            "wallet_balance_usd":round(balance/100,2),
            "candidate_evaluations":evaluations,
            "bids_submitted":bids
        }
    })
    leaderboard=sorted([
        {"lane":lane,"revenue_usd":round(v["earnings_total_cents"]/100,2),
         "completed":v["completed_jobs"],"accepted":v["accepted_jobs"],
         "bids":v["bids_submitted_total"],"score":v["earnings_total_cents"]*1000+v["completed_jobs"]*100+v["accepted_jobs"]*10+v["bids_submitted_total"]}
        for lane,v in agents.items()
    ], key=lambda x:x["score"], reverse=True)
    board["leaderboard"]=leaderboard

    now=datetime.fromisoformat(END)
    local_now=datetime.now(now.tzinfo)
    if local_now >= now and not board.get("finalized"):
        board["finalized"]=True
        board["finalized_at"]=now_iso()
        board["target_met"]=revenue/100 >= TARGET
        if board["target_met"]:
            winner=leaderboard[0]["lane"] if leaderboard else None
            board["winner"]=winner
            board["retired"]=[x["lane"] for x in leaderboard[1:]]
        else:
            board["winner"]=None
            board["retired"]=LANES[:]
        for lane in board["retired"]:
            p=ARENA/f"{lane}.json"
            ledger=load(p,{})
            ledger["status"]="RETIRED"
            ledger["retired"]=True
            ledger["retired_at"]=now_iso()
            save(p,ledger)

    runtime=load(RUNTIME,{"target_usd":5000,"collected_usd":0})
    runtime["arena"]=board
    runtime["collected_usd"]=round(revenue/100,2)
    runtime["last_cycle"]=now_iso()
    runtime["last_error"]="; ".join(errors) if errors else None
    runtime["audit"]={
        "arena_v1":True,
        "token_vault":True,
        "five_lanes":len(LANES),
        "verified_wallet":True,
        "candidate_evaluations":evaluations,
        "bids_submitted":bids,
        "target_usd_12h":TARGET
    }
    RUNTIME.write_text(json.dumps(runtime,indent=2,ensure_ascii=False)+"\\n",encoding="utf-8")
    save(BOARD,board)
    print(json.dumps({"revenue_usd":round(revenue/100,2),"target_usd":TARGET,"target_met":revenue/100>=TARGET,"finalized":board.get("finalized"),"evaluations":evaluations,"bids":bids},ensure_ascii=False))

if __name__=="__main__":
    main()
