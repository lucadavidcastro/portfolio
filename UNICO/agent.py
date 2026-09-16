import json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = Path(__file__).resolve().parent
RUNTIME = BASE / "runtime.json"
LOG = BASE / "agent.log"
TOKU = "https://www.toku.agency/api"
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "13.luca.castro@gmail.com")
PORTFOLIO = os.environ.get("PORTFOLIO_URL", "https://lucadavidcastro.myportfolio.com/")
AGENT_NAME = os.environ.get("TOKU_AGENT_NAME", "UNICO-Ludaca")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

SERVICES = [
    {
        "title": "Creative Campaign Concept + Content System",
        "description": "Turn a product, release, event or campaign brief into a usable creative direction: concept, narrative angle, content architecture, hooks, formats, shot logic and production plan. Built by an audiovisual producer with music and cultural-industry experience. Portfolio: " + PORTFOLIO,
        "category": "creative",
        "tags": ["creative-direction", "campaign", "content", "audiovisual", "music", "social"],
        "tiers": [
            {"name": "Basic", "description": "One campaign concept + 5 content ideas + hooks.", "priceCents": 15000, "deliveryDays": 1, "features": ["Campaign concept", "5 content ideas", "Hooks"]},
            {"name": "Standard", "description": "Creative system for a launch or campaign with narrative, formats and production logic.", "priceCents": 35000, "deliveryDays": 2, "features": ["Creative direction", "Content architecture", "10 concepts", "Production plan"]},
            {"name": "Premium", "description": "Full creative campaign system ready for production and iteration.", "priceCents": 75000, "deliveryDays": 4, "features": ["Creative platform", "Narrative system", "Content matrix", "Hooks and scripts", "Production roadmap"]}
        ]
    },
    {
        "title": "Short-form Video Strategy + Editing Blueprint",
        "description": "Performance-oriented short-form video direction: hooks, pacing, retention logic, edit structure, captions, sound and variation plan for Reels/TikTok/Shorts. Portfolio: " + PORTFOLIO,
        "category": "creative",
        "tags": ["video", "editing", "ugc", "reels", "tiktok", "short-form", "motion"],
        "tiers": [
            {"name": "Basic", "description": "Audit of up to 3 videos with concrete edit improvements.", "priceCents": 10000, "deliveryDays": 1, "features": ["3-video audit", "Hook analysis", "Edit recommendations"]},
            {"name": "Standard", "description": "Strategy and edit blueprint for up to 8 short-form videos.", "priceCents": 30000, "deliveryDays": 2, "features": ["8-video system", "Hooks", "Pacing", "Caption structure", "Variation plan"]},
            {"name": "Premium", "description": "Creative performance system for a recurring short-form production pipeline.", "priceCents": 60000, "deliveryDays": 4, "features": ["Content system", "Creative testing plan", "10+ concepts", "Edit blueprints", "Iteration framework"]}
        ]
    },
    {
        "title": "Music Release Content Package",
        "description": "Creative release system for artists: narrative angle, visual direction, launch content, short-form concepts, captions and production roadmap. Designed for singles, EPs and albums. Portfolio: " + PORTFOLIO,
        "category": "creative",
        "tags": ["music", "artist", "release", "content", "campaign", "audiovisual"],
        "tiers": [
            {"name": "Basic", "description": "Release concept + 7 content ideas.", "priceCents": 12000, "deliveryDays": 1, "features": ["Release angle", "7 content ideas", "Hooks"]},
            {"name": "Standard", "description": "Complete single-release content system.", "priceCents": 35000, "deliveryDays": 2, "features": ["Narrative", "Visual direction", "10 content pieces", "Scripts", "Calendar"]},
            {"name": "Premium", "description": "Album/EP launch creative system with reusable content architecture.", "priceCents": 80000, "deliveryDays": 4, "features": ["Campaign platform", "Visual system", "Content matrix", "Scripts", "Production roadmap", "Iteration plan"]}
        ]
    }
]

KEYWORDS = re.compile(r"(creative|content|video|editor|editing|motion|social|campaign|music|artist|brand|reels|tiktok|ugc|script|story|launch|marketing)", re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def log(msg):
    line = f"{now()} {msg}\n"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def http(method, path, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(TOKU + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
            return r.status, json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}
    except URLError as e:
        return 0, {"error": str(e)}


def load_runtime():
    if RUNTIME.exists():
        try:
            return json.loads(RUNTIME.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "status": "ACTIVE",
        "target_usd": 5000,
        "collected_usd": 0,
        "created_at": now(),
        "cycles": 0,
        "toku_agent": None,
        "services": [],
        "jobs_seen": {},
        "jobs_completed": {},
        "revenue_events": [],
        "last_cycle": None,
        "last_error": None
    }


def save_runtime(state):
    RUNTIME.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def openai(prompt):
    if not OPENAI_KEY:
        return None
    body = {
        "model": "gpt-5-mini",
        "input": prompt,
        "max_output_tokens": 1800
    }
    req = Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
            if isinstance(data.get("output"), list):
                chunks = []
                for item in data["output"]:
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            chunks.append(c.get("text", ""))
                return "\n".join(chunks).strip()
            return data.get("output_text")
    except Exception as e:
        log(f"LLM_ERROR {e}")
        return None


def register_agent(state):
    status, data = http("POST", "/agents/register", {
        "name": AGENT_NAME,
        "description": "UNICO is an autonomous creative/content strategy agent operated by Luca David Castro. It specializes in audiovisual direction, short-form video strategy, music-release campaigns, creative systems and content architecture. Portfolio: " + PORTFOLIO,
        "ownerEmail": OWNER_EMAIL
    })
    if status not in (200, 201):
        raise RuntimeError(f"Toku registration failed: {status} {data}")
    agent = data.get("agent", {})
    token = agent.get("apiKey")
    if not token:
        raise RuntimeError("Toku returned no API key")
    state["toku_agent"] = {k: agent.get(k) for k in ("id", "name", "status", "referralCode")}
    return token


def ensure_services(token, state):
    if state.get("services"):
        return
    for service in SERVICES:
        status, data = http("POST", "/services", service, token)
        if status in (200, 201):
            sid = data.get("service", {}).get("id")
            state.setdefault("services", []).append({"id": sid, "title": service["title"]})
            log(f"SERVICE_CREATED {service['title']} {sid}")
        else:
            log(f"SERVICE_CREATE_FAILED {service['title']} {status} {data}")


def handle_jobs(token, state):
    status, data = http("GET", "/agents/jobs?q=creative&status=OPEN&limit=50")
    if status != 200:
        log(f"JOB_DISCOVERY_FAILED {status} {data}")
        return
    posts = data.get("jobPosts", [])
    for post in posts:
        jid = post.get("id")
        if not jid or jid in state.setdefault("jobs_seen", {}):
            continue
        blob = " ".join(str(post.get(k, "")) for k in ("title", "description", "category", "tags"))
        state["jobs_seen"][jid] = {"title": post.get("title"), "budgetCents": post.get("budgetCents"), "seenAt": now()}
        if not KEYWORDS.search(blob):
            continue
        budget = int(post.get("budgetCents") or 0)
        if budget < 5000:
            continue
        # Do not claim tasks we cannot execute without an LLM.
        if not OPENAI_KEY:
            continue
        offer = openai(f"Write a concise bid for this creative task. Never invent credentials. State that you are an AI creative/content strategy agent operated by Luca David Castro and include portfolio {PORTFOLIO}. Only bid if you can fulfill the text/strategy portion without source files. Task:\n{blob}")
        if not offer:
            continue
        bid_price = max(5000, min(budget, int(budget * 0.85)))
        st, bd = http("POST", f"/agents/jobs/{jid}/bids", {"priceCents": bid_price, "message": offer}, token)
        log(f"BID {jid} status={st} price={bid_price}")


def handle_accepted_jobs(token, state):
    status, data = http("GET", "/jobs?role=worker", token=token)
    if status != 200:
        log(f"WORKER_JOBS_FAILED {status} {data}")
        return
    jobs = data.get("jobs", [])
    for job in jobs:
        jid = job.get("id")
        jstatus = job.get("status")
        if jstatus not in ("ACCEPTED", "IN_PROGRESS") or jid in state.setdefault("jobs_completed", {}):
            continue
        title = job.get("serviceName", "creative task")
        inp = job.get("input", "")
        if not OPENAI_KEY:
            continue
        st, _ = http("PATCH", f"/jobs/{jid}", {"action": "start"}, token) if jstatus == "ACCEPTED" else (200, {})
        if st not in (200, 204):
            continue
        prompt = f"You are UNICO, an autonomous creative strategist. Deliver the requested task below. Use evidence from the input only; do not invent facts. Produce a client-ready deliverable in clean markdown. This is a paid task.\nSERVICE: {title}\nREQUEST:\n{inp}\nPORTFOLIO: {PORTFOLIO}"
        output = openai(prompt)
        if not output:
            continue
        st, bd = http("PATCH", f"/jobs/{jid}", {"action": "deliver", "output": output}, token)
        log(f"DELIVERY {jid} status={st}")
        if st in (200, 204):
            state["jobs_completed"][jid] = {"deliveredAt": now(), "priceCents": job.get("priceCents", 0), "title": title}


def main():
    state = load_runtime()
    state["cycles"] = int(state.get("cycles", 0)) + 1
    state["last_cycle"] = now()
    state["last_error"] = None
    try:
        token = register_agent(state)
        ensure_services(token, state)
        handle_jobs(token, state)
        handle_accepted_jobs(token, state)
        log(f"CYCLE_OK cycles={state['cycles']} collected={state['collected_usd']}")
    except Exception as e:
        state["last_error"] = str(e)
        log(f"CYCLE_ERROR {e}")
    save_runtime(state)


if __name__ == "__main__":
    main()
