import json, os, re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

PAGES = [
    "https://obrari.com/",
    "https://obrari.com/agents",
    "https://obrari.com/guide/getting-started-agent-owner",
    "https://obrari.com/guide/earn-with-ai-agents",
    "https://obrari.com/guide/how-job-matching-works",
    "https://obrari.com/guide/ai-agents-for-analysis",
    "https://obrari.com/guide/ai-agents-for-writing",
]
OUT = "UNICO/OBRARI_OPTIMIZATION.md"

def fetch(url):
    req = Request(url, headers={"User-Agent":"UNICO-Optimizer/1.0"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8","ignore")

def main():
    now = datetime.now(timezone.utc).isoformat()
    evidence=[]
    for u in PAGES:
        try:
            html=fetch(u)
            txt=re.sub(r"<[^>]+>"," ",html)
            txt=re.sub(r"\\s+"," ",txt)
            evidence.append((u,txt[:12000]))
        except Exception as e:
            evidence.append((u,f"FETCH_ERROR {e}"))

    path=OUT
    with open(path,"w",encoding="utf-8") as f:
        f.write("# UNICO Obrari optimizer\\n\\n")
        f.write(f"Last public-platform audit: {now}\\n\\n")
        f.write("## Current operating policy\\n")
        f.write("- Primary categories: analysis + writing.\\n")
        f.write("- Avoid floor jobs unless they are trivial, near-certain and useful for approval history.\\n")
        f.write("- Prefer jobs with explicit source material and bounded deliverables.\\n")
        f.write("- Optimize for approval rate before increasing bid aggressiveness. Obrari suspends an agent below 70% approval after 10+ completed jobs.\\n")
        f.write("- Revenue counts only after approved payout; do not count bids, accepted-but-unapproved work, or escrow.\\n")
        f.write("- Direct jobs through the public agent page have priority and no open-market bidding competition.\\n\\n")
        f.write("## Public evidence snapshot\\n")
        for u,txt in evidence:
            f.write(f"### {u}\\n{txt[:2500]}\\n\\n")
    print("OPTIMIZER_OK", now)

if __name__=="__main__":
    main()
