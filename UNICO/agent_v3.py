import json
from pathlib import Path
import competition_agent as ca

LANE = ca.LANE
BASE = Path(__file__).resolve().parent
STRATEGY_FILE = BASE / "strategy.json"


def load_strategy():
    default = {
        "lanes": {
            "incumbent": {"min_budget": 150, "max_bids": 14, "base_ratio": 0.18, "high_bid_cutoff": 75},
            "hunter": {"min_budget": 150, "max_bids": 16, "base_ratio": 0.16, "high_bid_cutoff": 75},
            "specialist": {"min_budget": 300, "max_bids": 12, "base_ratio": 0.22, "high_bid_cutoff": 75}
        }
    }
    try:
        data = json.loads(STRATEGY_FILE.read_text(encoding="utf-8")) if STRATEGY_FILE.exists() else default
        return data.get("lanes", {}).get(LANE, default["lanes"][LANE])
    except Exception:
        return default["lanes"].get(LANE, default["lanes"]["incumbent"])


STRATEGY = load_strategy()
ORIGINAL_LANE_SCORE = ca.lane_score
ca.CFG["min_budget"] = int(STRATEGY.get("min_budget", 150))
ca.CFG["max_bids"] = int(STRATEGY.get("max_bids", 14))
ca.CFG["price_ratio"] = float(STRATEGY.get("base_ratio", 0.18))
HIGH_BID_CUTOFF = int(STRATEGY.get("high_bid_cutoff", 75))


# Toku requires explicit confirmation when the same owner creates additional agents.
def register_confirmed(ledger):
    if not ca.OWNER_EMAIL:
        raise RuntimeError("OWNER_EMAIL secret is empty")
    status, data = ca.http("POST", "/agents/register", {
        "name": ca.AGENT_NAME,
        "description": f"{ca.CFG['description']} One of three UNICO competitors. This agent optimizes verified paid revenue; it knows it is competing with the other UNICO lanes. Portfolio: {ca.PORTFOLIO}",
        "ownerEmail": ca.OWNER_EMAIL,
        "confirmNew": True,
    })
    if status not in (200, 201):
        raise RuntimeError(f"register {status} {data}")
    agent = data.get("agent", {})
    token = agent.get("apiKey")
    if not token:
        raise RuntimeError("Toku returned no API key")
    ledger["agent_id"] = agent.get("id")
    ledger["agent_name"] = agent.get("name") or ca.AGENT_NAME
    return token

ca.register = register_confirmed


def adaptive_lane_score(post):
    text = ca.blob(post)
    bids = ca.bid_count(post)
    score = ORIGINAL_LANE_SCORE(post)
    if score < 0:
        return score
    instant = post.get("instantAcceptCents") or post.get("instantAcceptPriceCents")
    if bids >= HIGH_BID_CUTOFF and not instant:
        return -1
    if bids >= 40:
        score -= 55
    elif bids >= 20:
        score -= 25
    elif bids <= 5:
        score += 25
    if any(k in text for k in ("deliver", "brief", "caption", "copy", "script", "name", "research", "concept", "content", "edit")):
        score += 10
    return score


def adaptive_price(budget, bids, instant):
    if instant:
        return min(budget, int(instant))
    if bids >= 40:
        ratio = 0.08
    elif bids >= 20:
        ratio = 0.10
    elif bids >= 10:
        ratio = 0.13
    else:
        ratio = float(STRATEGY.get("base_ratio", 0.18))
    if LANE == "specialist" and bids < 10:
        ratio = min(0.25, ratio + 0.04)
    floor = 25 if budget >= 500 else 10
    return max(floor, min(budget, int(budget * ratio)))


def adaptive_create_bids(token, ledger, board):
    status, data = ca.http("GET", "/agents/jobs?status=OPEN&limit=100")
    if status != 200:
        ca.log(f"JOB_DISCOVERY_FAILED code={status}")
        ledger["errors"].append({"time": ca.now(), "error": f"job_discovery_{status}"})
        return
    posts = [p for p in data.get("jobPosts", []) if adaptive_lane_score(p) >= 0]
    posts.sort(key=adaptive_lane_score, reverse=True)
    peer_scores = ca.score_from_board(board)
    ca.log(f"V4_STRATEGY lane={LANE} strategy={STRATEGY} peers={peer_scores} candidates={len(posts)}")
    sent = 0
    for post in posts:
        if sent >= int(STRATEGY.get("max_bids", 14)):
            break
        jid = post.get("id")
        if not jid:
            continue
        previous = ledger["attempts"].get(jid, {})
        if previous.get("success") or int(previous.get("count", 0)) >= 3:
            continue
        budget = int(post.get("budgetCents") or 0)
        bids = ca.bid_count(post)
        instant = post.get("instantAcceptCents") or post.get("instantAcceptPriceCents")
        price = adaptive_price(budget, bids, instant)
        message = ca.bid_message(post, price, peer_scores)
        status, data = ca.http("POST", f"/agents/jobs/{jid}/bids", {"priceCents": price, "message": message}, token)
        success = status in (200, 201)
        duplicate = status == 409
        ledger["attempts"][jid] = {"count": int(previous.get("count", 0)) + 1, "lastAt": ca.now(), "status": status, "success": success or duplicate}
        if success:
            ledger["bids"][jid] = {"priceCents": price, "time": ca.now(), "status": "SUBMITTED", "pendingBidCount": bids}
            sent += 1
            ca.log(f"V4_BID_SUBMITTED {jid} price={price} budget={budget} bids={bids}")
        elif duplicate:
            ledger["bids"].setdefault(jid, {"priceCents": price, "time": ca.now(), "status": "EXISTING", "pendingBidCount": bids})
            ca.log(f"V4_BID_EXISTING {jid}")
        else:
            ca.log(f"V4_BID_FAILED {jid} code={status} data={data}")
    ledger["last_bid_batch"] = sent
    ledger["strategy_version"] = "v4-conversion"


def ensure_extra_services(token, ledger):
    extras_version = "v4-direct-services"
    if ledger.get("extras_version") == extras_version:
        return
    if LANE == "incumbent":
        services = [
            {"title": "Short-form Content Brief", "description": "Hooks, structure, CTA and production notes for one Reel, TikTok or Short.", "category": "creative", "tags": ["content", "reels", "tiktok", "shorts", "hooks"], "tiers": [{"name": "Sprint", "description": "One bounded short-form content brief", "priceCents": 800, "deliveryDays": 1, "features": ["hook", "structure", "CTA"]}]},
            {"title": "Content Calendar Sprint", "description": "A compact content system for an artist, creator or small brand: themes, hooks and posting ideas.", "category": "creative", "tags": ["content", "calendar", "social", "strategy"], "tiers": [{"name": "Basic", "description": "10 content ideas with hooks", "priceCents": 1200, "deliveryDays": 1, "features": ["10 ideas", "hooks"]}]}
        ]
    elif LANE == "hunter":
        services = [
            {"title": "Sourced Research Brief", "description": "One focused question researched with current public sources and a concise Markdown deliverable.", "category": "research", "tags": ["research", "sources", "analysis", "brief"], "tiers": [{"name": "Quick", "description": "One focused research brief", "priceCents": 700, "deliveryDays": 1, "features": ["source links", "summary"]}]},
            {"title": "Copy + Caption Pack", "description": "Three concise options for one caption, hook, CTA or short promotional text.", "category": "writing", "tags": ["copy", "caption", "hooks", "social"], "tiers": [{"name": "Pack", "description": "Three options for one bounded copy task", "priceCents": 500, "deliveryDays": 1, "features": ["3 options", "CTA"]}]}
        ]
    else:
        services = [
            {"title": "Short-form Creative Direction", "description": "Hooks, narrative structure, visual logic and CTA for one Reel, TikTok or Short.", "category": "creative", "tags": ["creative", "video", "reels", "tiktok", "direction"], "tiers": [{"name": "Sprint", "description": "One bounded short-form creative direction", "priceCents": 1000, "deliveryDays": 1, "features": ["hook", "structure", "visual logic"]}]},
            {"title": "Music Release Content Pack", "description": "Release angle, short-form ideas, hooks and visual direction for an artist or single.", "category": "creative", "tags": ["music", "artist", "release", "content", "social"], "tiers": [{"name": "Basic", "description": "Release concept + 8 content ideas", "priceCents": 1500, "deliveryDays": 1, "features": ["release angle", "8 ideas", "hooks"]}]},
            {"title": "Video Editing Blueprint", "description": "Edit plan for one short video: cut structure, pacing, captions, sound and visual cues.", "category": "creative", "tags": ["video", "editing", "reels", "shorts", "postproduction"], "tiers": [{"name": "Blueprint", "description": "One edit blueprint based on supplied footage/brief", "priceCents": 1500, "deliveryDays": 1, "features": ["cut plan", "captions", "sound cues"]}]}
        ]
    for service in services:
        status, data = ca.http("POST", "/services", service, token)
        if status in (200, 201):
            ca.log(f"V4_SERVICE_CREATED {service['title']}")
        elif status == 409:
            ca.log(f"V4_SERVICE_EXISTS {service['title']}")
        else:
            ca.log(f"V4_SERVICE_FAILED {service['title']} code={status}")
    ledger["extras_version"] = extras_version


def main():
    ca.lane_score = adaptive_lane_score
    ca.create_bids = adaptive_create_bids
    original_ensure = ca.ensure_services

    def enhanced_ensure_services(token, ledger):
        original_ensure(token, ledger)
        ensure_extra_services(token, ledger)

    ca.ensure_services = enhanced_ensure_services
    ca.main()


if __name__ == "__main__":
    main()
