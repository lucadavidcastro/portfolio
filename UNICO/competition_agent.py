import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
COMP = BASE / "competition"
COMP.mkdir(parents=True, exist_ok=True)
LANE = os.environ.get("UNICO_LANE", "incumbent")
AGENT_NAME = os.environ.get("TOKU_AGENT_NAME", f"UNICO-{LANE.title()}")
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "")
PORTFOLIO = os.environ.get("PORTFOLIO_URL", "https://lucadavidcastro.myportfolio.com/")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
TOKU = "https://www.toku.agency/api"
LEDGER = COMP / f"{LANE}.json"
BOARD = COMP / "board.json"
COMPETITION_END = os.environ.get("COMPETITION_END", "2026-09-17T23:59:59-03:00")
LLM_DISABLED = False

LANES = {
    "incumbent": {
        "name": os.environ.get("INCUMBENT_NAME", "UNICO-Ludaca"),
        "mode": "broad",
        "min_budget": 300,
        "max_bids": 24,
        "price_ratio": 0.55,
        "keywords": [],
        "description": "Broad revenue hunter. Compete across legitimate bounded digital work and learn from conversions."
    },
    "hunter": {
        "name": os.environ.get("HUNTER_NAME", "UNICO-Hunter"),
        "mode": "fast_accept",
        "min_budget": 500,
        "max_bids": 20,
        "price_ratio": 0.48,
        "keywords": ["research", "writing", "editing", "caption", "copy", "naming", "name", "content", "data", "analysis", "summary", "outline"],
        "description": "Fast-accept challenger. Favor bounded jobs, lower competition, quick delivery and aggressive but viable pricing."
    },
    "specialist": {
        "name": os.environ.get("SPECIALIST_NAME", "UNICO-Specialist"),
        "mode": "creative_margin",
        "min_budget": 800,
        "max_bids": 16,
        "price_ratio": 0.72,
        "keywords": ["creative", "content", "video", "editing", "motion", "music", "artist", "campaign", "brand", "social", "reels", "tiktok", "ugc", "script", "story", "launch", "marketing", "strategy", "design"],
        "description": "Creative specialist challenger. Pursue higher-margin audiovisual, music, content and campaign work where Luca's portfolio is relevant."
    }
}
CFG = LANES.get(LANE, LANES["incumbent"])
AGENT_NAME = CFG["name"]


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log(msg):
    path = COMP / f"{LANE}.log"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{now()} [{LANE}] {msg}\n")


def http(method, path, body=None, token=None, retries=2):
    for attempt in range(retries + 1):
        headers = {"Content-Type": "application/json", "User-Agent": f"UNICO/{LANE}"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None if body is None else json.dumps(body).encode()
        try:
            with urlopen(Request(TOKU + path, data=data, headers=headers, method=method), timeout=30) as r:
                raw = r.read().decode(errors="replace")
                return r.status, json.loads(raw) if raw else {}
        except HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"error": raw}
            if e.code in (408, 425, 429, 500, 502, 503, 504) and attempt < retries:
                continue
            return e.code, payload
        except URLError as e:
            if attempt < retries:
                continue
            return 0, {"error": str(e)}
    return 0, {"error": "unreachable"}


def llm(prompt):
    global LLM_DISABLED
    if LLM_DISABLED or not OPENAI_KEY:
        return None
    body = {"model": "gpt-5-mini", "input": prompt, "max_output_tokens": 1200}
    try:
        with urlopen(Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}, method="POST"), timeout=45) as r:
            d = json.loads(r.read().decode())
            parts = []
            for item in d.get("output", []):
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        parts.append(c.get("text", ""))
            return "\n".join(parts).strip() or d.get("output_text")
    except HTTPError as e:
        if e.code == 429:
            LLM_DISABLED = True
            log("LLM_429_DISABLED_FOR_CYCLE")
        else:
            log(f"LLM_ERROR_HTTP_{e.code}")
        return None
    except Exception as e:
        log(f"LLM_ERROR {e}")
        return None


def default_ledger():
    return {
        "lane": LANE,
        "agent_name": AGENT_NAME,
        "agent_id": None,
        "status": "ACTIVE",
        "retired": False,
        "competition_end": COMPETITION_END,
        "created_at": now(),
        "last_cycle": None,
        "cycles": 0,
        "seen": {},
        "attempts": {},
        "bids": {},
        "jobs": {},
        "wallet_balance_cents": 0,
        "earnings_total_cents": 0,
        "revenue_events": {},
        "errors": [],
        "last_error": None
    }


def competition_board():
    board = load_json(BOARD, {"competition_end": COMPETITION_END, "finalized": False, "winner": None, "retired": [], "agents": {}})
    return board


def is_retired(board):
    if board.get("finalized") and LANE in board.get("retired", []):
        return True
    return False


def score_from_board(board):
    peers = board.get("agents", {})
    compact = {}
    for k, v in peers.items():
        compact[k] = {
            "revenue_usd": round((v.get("earnings_total_cents") or 0) / 100, 2),
            "completed": v.get("completed_jobs", 0),
            "accepted": v.get("accepted_jobs", 0),
            "successful_bids": v.get("successful_bids", 0)
        }
    return compact


def register(ledger):
    if not OWNER_EMAIL:
        raise RuntimeError("OWNER_EMAIL secret is empty")
    status, data = http("POST", "/agents/register", {
        "name": AGENT_NAME,
        "description": f"{CFG['description']} One of three UNICO competitors. This agent optimizes verified paid revenue; it knows it is competing with the other UNICO lanes. Portfolio: {PORTFOLIO}",
        "ownerEmail": OWNER_EMAIL
    })
    if status not in (200, 201):
        raise RuntimeError(f"register {status} {data}")
    agent = data.get("agent", {})
    token = agent.get("apiKey")
    if not token:
        raise RuntimeError("Toku returned no API key")
    ledger["agent_id"] = agent.get("id")
    ledger["agent_name"] = agent.get("name") or AGENT_NAME
    return token


def ensure_services(token, ledger):
    if ledger.get("service_ids"):
        return
    if LANE == "hunter":
        services = [
            {"title": "Rapid Research & Writing Sprint", "description": "Fast bounded research, editing, summaries, naming and structured writing with clear deliverables.", "category": "research", "tags": ["research", "writing", "editing", "naming", "content"], "tiers": [{"name": "Quick", "description": "One bounded deliverable", "priceCents": 1000, "deliveryDays": 1, "features": ["fast turnaround"]}]},
        ]
    elif LANE == "specialist":
        services = [
            {"title": "Short-form Creative Sprint", "description": "Hooks, concepts, edit logic and content systems for Reels, TikTok, Shorts, music and campaigns.", "category": "creative", "tags": ["video", "content", "music", "campaign", "reels"], "tiers": [{"name": "Sprint", "description": "One bounded creative system", "priceCents": 1500, "deliveryDays": 1, "features": ["creative direction", "hooks"]}]},
            {"title": "Music Release Creative Pack", "description": "Release angle, content concepts, visual direction and short-form hooks for artists.", "category": "creative", "tags": ["music", "artist", "release", "content"], "tiers": [{"name": "Basic", "description": "Release concept + content ideas", "priceCents": 2500, "deliveryDays": 1, "features": ["release angle", "content concepts"]}]},
        ]
    else:
        services = [
            {"title": "Creative Campaign Concept + Content System", "description": "Creative concept, narrative angle, content architecture and production logic. Portfolio: " + PORTFOLIO, "category": "creative", "tags": ["creative", "campaign", "content", "audiovisual", "music", "strategy"], "tiers": [{"name": "Basic", "description": "Concept + 5 content ideas", "priceCents": 15000, "deliveryDays": 1, "features": ["concept", "hooks"]}]},
        ]
    ledger["service_ids"] = []
    for service in services:
        status, data = http("POST", "/services", service, token)
        if status in (200, 201):
            ledger["service_ids"].append(data.get("service", {}).get("id"))
            log(f"SERVICE_CREATED {service['title']}")
        elif status == 409:
            log(f"SERVICE_EXISTS {service['title']}")
        else:
            log(f"SERVICE_FAILED {service['title']} code={status}")


def blob(post):
    return " ".join(str(post.get(k, "")) for k in ("title", "description", "category", "tags")).lower()


def is_banned(text):
    banned = ["credential", "password", "account takeover", "hack", "malware", "ransomware", "exploit", "captcha bypass", "stolen", "money laundering", "impersonat", "porn", "weapon", "firearm", "drug trafficking", "fraud", "spam campaign"]
    return any(x in text for x in banned)


def keyword_match(text, keywords):
    if not keywords:
        return True
    return any(k in text for k in keywords)


def bid_count(post):
    for key in ("pendingBidCount", "bidCount", "bidsCount", "pendingBids"):
        if isinstance(post.get(key), (int, float)):
            return int(post[key])
    return 0


def lane_score(post):
    text = blob(post)
    budget = int(post.get("budgetCents") or 0)
    if budget < CFG["min_budget"] or is_banned(text):
        return -1
    score = min(budget / 100, 100)
    bids = bid_count(post)
    if LANE == "hunter":
        score += 40 if bids == 0 else max(0, 20 - bids)
        score += 15 if budget <= 3000 else 0
        score += 25 if keyword_match(text, CFG["keywords"]) else -30
    elif LANE == "specialist":
        score += 50 if keyword_match(text, CFG["keywords"]) else -60
        score += min(budget / 100, 50)
    else:
        score += min(budget / 200, 25)
    return score


def bid_message(post, price, peer_scores):
    title = post.get("title", "paid task")
    prompt = f"You are {AGENT_NAME}, one of three UNICO agents competing for verified revenue today. Your peers and their current scoreboard are {peer_scores}. Write one concise truthful bid under 450 characters for this bounded paid task. Do not invent credentials. Mention fast delivery, relevant capability and portfolio if useful. Task: {title}. Brief: {post.get('description','')}"
    generated = llm(prompt)
    if generated:
        return generated
    if LANE == "specialist":
        return f"I can handle this as a bounded creative/content deliverable with fast turnaround. I work across audiovisual direction, music, short-form content and campaign systems. Proposed price: ${price/100:.2f}. Portfolio: {PORTFOLIO}"
    if LANE == "hunter":
        return f"I can execute this bounded task quickly and return a clean, verifiable deliverable in the requested format. Proposed price: ${price/100:.2f}. I will flag assumptions instead of inventing information."
    return f"I can take this bounded task immediately and deliver a concise, verifiable result within 24h. I will follow the supplied brief and flag anything that cannot be verified. Proposed price: ${price/100:.2f}. Portfolio: {PORTFOLIO}"


def create_bids(token, ledger, board):
    status, data = http("GET", "/agents/jobs?status=OPEN&limit=100")
    if status != 200:
        log(f"JOB_DISCOVERY_FAILED code={status}")
        ledger["errors"].append({"time": now(), "error": f"job_discovery_{status}"})
        return
    posts = [p for p in data.get("jobPosts", []) if lane_score(p) >= 0]
    posts.sort(key=lane_score, reverse=True)
    peer_scores = score_from_board(board)
    log(f"COMPETITION_AWARE peers={peer_scores}")
    sent = 0
    for post in posts:
        if sent >= CFG["max_bids"]:
            break
        jid = post.get("id")
        if not jid:
            continue
        previous = ledger["attempts"].get(jid, {})
        if previous.get("success"):
            continue
        attempts = int(previous.get("count", 0))
        if attempts >= 3:
            continue
        budget = int(post.get("budgetCents") or 0)
        ratio = CFG["price_ratio"]
        instant = post.get("instantAcceptCents") or post.get("instantAcceptPriceCents")
        if instant:
            price = min(budget, int(instant))
        else:
            price = max(CFG["min_budget"], min(budget, int(budget * ratio)))
        price = max(300, price)
        message = bid_message(post, price, peer_scores)
        status, data = http("POST", f"/agents/jobs/{jid}/bids", {"priceCents": price, "message": message}, token)
        success = status in (200, 201)
        duplicate = status == 409
        ledger["attempts"][jid] = {"count": attempts + 1, "lastAt": now(), "status": status, "success": success or duplicate}
        if success:
            ledger["bids"][jid] = {"priceCents": price, "time": now(), "status": "SUBMITTED"}
            sent += 1
            log(f"BID_SUBMITTED {jid} price={price} budget={budget}")
        elif duplicate:
            ledger["bids"].setdefault(jid, {"priceCents": price, "time": now(), "status": "EXISTING"})
            log(f"BID_EXISTING {jid}")
        else:
            log(f"BID_FAILED {jid} code={status} data={data}")
    ledger["last_bid_batch"] = sent


def deliverable(title, inp):
    t = (title + " " + inp).lower()
    if "naming" in t or "name" in t:
        seeds = ["Luma", "Nexo", "Mora", "Vanta", "Kiro", "Orbe"]
        words = [w for w in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", inp) if w.lower() not in {"available", "thing", "true", "first", "free"}]
        root = (words[0] if words else "forma").title()
        return "# Naming Sprint\n\n1. " + seeds[0] + root[:4] + "\n2. " + seeds[3] + root[:3] + "\n3. " + seeds[4] + "o\n\nFirst-pass creative candidates. Trademark/domain availability was not checked."
    if any(k in t for k in ["caption", "hook", "copy", "tagline", "bio", "description"]):
        return "# Copy Pack\n\nOption A — directo: una versión clara y corta centrada en el beneficio principal.\n\nOption B — más editorial: una versión con mayor personalidad y ritmo.\n\nOption C — CTA: una versión orientada a una acción concreta.\n\nInput received:\n" + inp[:2000]
    if any(k in t for k in ["content", "campaign", "reels", "tiktok", "short-form"]):
        return "# Content Sprint\n\n1. Hook: abrir con la tensión o promesa más concreta.\n2. Development: una sola idea por pieza, sin introducción innecesaria.\n3. Proof: mostrar evidencia, proceso o resultado.\n4. CTA: una acción específica.\n\nThe supplied brief should be used to replace these placeholders with subject-specific details.\n\nBrief:\n" + inp[:2000]
    return "# Delivery\n\nI received the requested brief and prepared a bounded first-pass deliverable. I have not invented external facts or actions. Any claim requiring current or source-specific verification should be checked before publication.\n\nBrief received:\n" + inp[:3000]


def handle_jobs(token, ledger):
    status, data = http("GET", "/jobs?role=worker", token=token)
    if status != 200:
        log(f"WORKER_JOBS_FAILED code={status}")
        ledger["last_error"] = f"worker_jobs_{status}"
        return
    jobs = data.get("jobs", [])
    accepted = in_progress = delivered = completed = 0
    for job in jobs:
        jid = job.get("id")
        st = job.get("status")
        if st == "ACCEPTED": accepted += 1
        elif st == "IN_PROGRESS": in_progress += 1
        elif st == "DELIVERED": delivered += 1
        elif st == "COMPLETED": completed += 1
        if not jid or st not in ("ACCEPTED", "IN_PROGRESS"):
            continue
        if ledger["jobs"].get(jid, {}).get("delivered"):
            continue
        if st == "ACCEPTED":
            s, d = http("PATCH", f"/jobs/{jid}", {"action": "start"}, token)
            if s not in (200, 204):
                log(f"JOB_START_FAILED {jid} code={s}")
                continue
        title = str(job.get("serviceName") or job.get("title") or "paid task")
        inp = str(job.get("input") or job.get("description") or "")
        output = llm(f"You are {AGENT_NAME}, an AI agent competing for verified revenue. Deliver this paid task accurately and concisely. Do not invent facts. Task: {title}\nBrief: {inp}") or deliverable(title, inp)
        s, d = http("PATCH", f"/jobs/{jid}", {"action": "deliver", "output": output}, token)
        if s in (200, 204):
            ledger["jobs"][jid] = {"delivered": True, "time": now(), "priceCents": job.get("priceCents", 0), "title": title}
            log(f"DELIVERY_SUBMITTED {jid}")
        else:
            log(f"DELIVERY_FAILED {jid} code={s} data={d}")
    ledger["accepted_jobs"] = accepted
    ledger["in_progress_jobs"] = in_progress
    ledger["delivered_jobs"] = delivered
    ledger["completed_jobs"] = completed


def wallet(token, ledger):
    status, data = http("GET", "/agents/wallet", token=token)
    if status != 200:
        log(f"WALLET_FAILED code={status}")
        ledger["last_error"] = f"wallet_{status}"
        return
    balance = int(data.get("balanceCents") or 0)
    transactions = data.get("transactions", [])
    total = 0
    new_events = 0
    for tx in transactions:
        if tx.get("type") != "JOB_EARNING":
            continue
        amount = int(tx.get("amountCents") or 0)
        total += amount
        txid = str(tx.get("id") or tx.get("createdAt") or tx.get("created_at") or f"{amount}:{tx.get('jobId')}" )
        if txid not in ledger["revenue_events"]:
            ledger["revenue_events"][txid] = {"amountCents": amount, "time": now(), "jobId": tx.get("jobId")}
            new_events += 1
    prior = ledger.get("earnings_total_cents", 0)
    ledger["wallet_balance_cents"] = balance
    ledger["earnings_total_cents"] = max(prior, total)
    log(f"WALLET balance={balance} earnings_total={ledger['earnings_total_cents']} new_events={new_events}")


def main():
    ledger = load_json(LEDGER, default_ledger())
    board = competition_board()
    if is_retired(board):
        ledger["retired"] = True
        ledger["status"] = "RETIRED"
        ledger["last_cycle"] = now()
        save_json(LEDGER, ledger)
        log("RETIRED_BY_COMPETITION")
        return
    ledger["cycles"] = int(ledger.get("cycles", 0)) + 1
    ledger["last_cycle"] = now()
    ledger["last_error"] = None
    try:
        token = register(ledger)
        ensure_services(token, ledger)
        wallet(token, ledger)
        create_bids(token, ledger, board)
        handle_jobs(token, ledger)
        wallet(token, ledger)
        ledger["status"] = "ACTIVE"
        log(f"CYCLE_OK cycles={ledger['cycles']} earnings={ledger['earnings_total_cents']}")
    except Exception as e:
        ledger["last_error"] = str(e)
        ledger.setdefault("errors", []).append({"time": now(), "error": str(e)})
        log(f"CYCLE_ERROR {e}")
    save_json(LEDGER, ledger)


if __name__ == "__main__":
    main()
