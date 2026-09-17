import competition_agent


def register_confirmed(ledger):
    if not competition_agent.OWNER_EMAIL:
        raise RuntimeError("OWNER_EMAIL secret is empty")
    status, data = competition_agent.http("POST", "/agents/register", {
        "name": competition_agent.AGENT_NAME,
        "description": f"{competition_agent.CFG['description']} One of three UNICO competitors. This agent optimizes verified paid revenue; it knows it is competing with the other UNICO lanes. Portfolio: {competition_agent.PORTFOLIO}",
        "ownerEmail": competition_agent.OWNER_EMAIL,
        "confirmNew": True,
    })
    if status not in (200, 201):
        raise RuntimeError(f"register {status} {data}")
    agent = data.get("agent", {})
    token = agent.get("apiKey")
    if not token:
        raise RuntimeError("Toku returned no API key")
    ledger["agent_id"] = agent.get("id")
    ledger["agent_name"] = agent.get("name") or competition_agent.AGENT_NAME
    return token


# Toku requires explicit confirmation when the same owner creates additional agents.
competition_agent.register = register_confirmed

if __name__ == "__main__":
    competition_agent.main()
