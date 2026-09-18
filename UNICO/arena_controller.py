import json
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent
ARENA=BASE/"arena"
STRATEGY=ARENA/"strategy.json"
LANES=["sniper","research","creative","builder","premium"]

def load():
    return json.loads(STRATEGY.read_text(encoding="utf-8"))

def main():
    data=load()
    now=datetime.now(timezone.utc)
    data["last_controller_run"]=now.isoformat()
    data["control_version"]="arena-v1"
    for lane in LANES:
        cfg=data.setdefault("runtime",{}).setdefault(lane,{})
        cfg["enabled"]=True
        cfg["last_control"]=now.isoformat()
    STRATEGY.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"
",encoding="utf-8")
    print("ARENA_CONTROLLER_OK")
if __name__=="__main__":
    main()
