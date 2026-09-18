# UNICO Failure Audit — 2026-09-17

## Confirmed failures in the previous architecture

1. `agent_v3.py` did not increment `cycles`, update `last_cycle`, reconcile wallet earnings, or maintain the official `collected_usd` field. A successful workflow could therefore coexist with stale economic state.
2. `agent_v3.py` marked a job as seen before the bid result. A transient 429/500/network failure could permanently suppress later retries for that job.
3. OpenAI HTTP 429 errors were retried independently for multiple tasks in the same cycle instead of opening a cycle-level circuit breaker.
4. The previous workflow could have multiple executions close together without an explicit concurrency guard.
5. The previous `agent_v3.py` relied on one broad bidding lane, so volume was confused with conversion quality.
6. Acceptance and delivery monitoring existed only partially and was not incorporated into the official revenue ledger.
7. Wallet state was not reconciled after delivery in the active v3 workflow.
8. There was no competitive experiment to identify which pricing/selection strategy actually produced verified revenue.
9. The Toku webhook setup remains incomplete. Email notifications are active, but the webhook setup is not.
10. Obrari was researched as a second channel, but it cannot be activated automatically from the current environment because the platform requires an Obrari owner account plus an LLM provider key configured in the platform. This remains a deployment dependency, not a claimed active revenue channel.

## Mitigations now deployed

- Three autonomous lanes: `incumbent`, `hunter`, `specialist`.
- Competition-aware descriptions and peer scoreboard.
- Per-lane durable ledgers under `UNICO/competition/`.
- Explicit wallet polling and verified `JOB_EARNING` reconciliation.
- Acceptance/in-progress/delivered/completed status tracking.
- Bid retry accounting with a bounded retry count.
- Cycle-level LLM 429 circuit breaker.
- GitHub Actions concurrency lock.
- One reconciliation job owns the official `runtime.json` update.
- End-of-day ranking by verified revenue first, then completed/accepted/successful-bid tie-breakers.
- Losing lanes are retired after the competition closes.
- Revenue remains zero until wallet evidence proves otherwise.

## Day-7 scale backlog

- Add a live second marketplace lane once Obrari credentials are available.
- Add multi-provider LLM routing (OpenAI/Google/Anthropic/OpenAI-compatible providers) so one provider outage cannot stall execution.
- Add historical conversion scoring by platform, category, price and lane.
- Add direct-client acquisition and referral tracking.
- Add automated model/cost selection based on expected margin.

## Adaptive controller 2026-09-17T18:01:25.761952+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.1800->0.1476; crowded-job cutoff 75->65
- hunter: zero acceptance after 40 bids -> ratio 0.1600->0.1312; crowded-job cutoff 75->65
- specialist: zero acceptance after 32 bids -> ratio 0.2200->0.1804; crowded-job cutoff 75->65
- Aggregate bids: 120
- Verified revenue: USD 0.00

## Adaptive controller 2026-09-17T18:58:52.400547+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.1476->0.1210; crowded-job cutoff 65->55
- hunter: zero acceptance after 40 bids -> ratio 0.1312->0.1076; crowded-job cutoff 65->55
- specialist: zero acceptance after 32 bids -> ratio 0.1804->0.1479; crowded-job cutoff 65->55
- Aggregate bids: 120
- Verified revenue: USD 0.00

## Adaptive controller 2026-09-17T21:55:42.714524+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.1210->0.0992; crowded-job cutoff 55->45
- hunter: zero acceptance after 40 bids -> ratio 0.1076->0.0882; crowded-job cutoff 55->45
- specialist: zero acceptance after 32 bids -> ratio 0.1479->0.1213; crowded-job cutoff 55->45
- Aggregate bids: 120
- Verified revenue: USD 0.00

## Adaptive controller 2026-09-17T23:47:59.233123+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.0992->0.0813; crowded-job cutoff 45->40
- hunter: zero acceptance after 40 bids -> ratio 0.0882->0.0800; crowded-job cutoff 45->40
- specialist: zero acceptance after 32 bids -> ratio 0.1213->0.0995; crowded-job cutoff 45->40
- Aggregate bids: 120
- Verified revenue: USD 0.00

## Adaptive controller 2026-09-18T01:35:43.487125+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.0813->0.0800; crowded-job cutoff 40->40
- hunter: zero acceptance after 40 bids -> ratio 0.0800->0.0800; crowded-job cutoff 40->40
- specialist: zero acceptance after 32 bids -> ratio 0.0995->0.0816; crowded-job cutoff 40->40
- Aggregate bids: 120
- Verified revenue: USD 0.00

## Adaptive controller 2026-09-18T02:35:20.943306+00:00

- incumbent: zero acceptance after 48 bids -> ratio 0.0800->0.0800; crowded-job cutoff 40->40
- hunter: zero acceptance after 40 bids -> ratio 0.0800->0.0800; crowded-job cutoff 40->40
- specialist: zero acceptance after 32 bids -> ratio 0.0816->0.0800; crowded-job cutoff 40->40
- Aggregate bids: 120
- Verified revenue: USD 0.00



## Full-system audit — Arena v1 — 2026-09-18

### Critical defects found and retired

11. **Agent multiplication bug.** The legacy `agent_v3.py` replaced `competition_agent.register` with a function that always called `/agents/register` with `confirmNew: true`. It ran every scheduled cycle, so the system could create another Toku agent instead of reusing the existing agent token. The persisted ledgers showed 10 cycles per lane after activation; logs show a fresh successful registration at each of those cycles. This architecture is now retired.
12. **Monkey-patch recursion.** The legacy v4 wrapper assigned `ca.lane_score = adaptive_lane_score` and then called `ca.lane_score()` from inside `adaptive_lane_score()`, producing `maximum recursion depth exceeded` in all three lanes. This is retired with the wrapper.
13. **Disconnected control plane.** The adaptive controller changed `strategy.json`, but the legacy engine still had its own hard-coded lane configuration and only partially imported strategy state. The controller could therefore report a strategy change without guaranteeing execution of that change.
14. **Two active schedulers risk.** The legacy workflow and the new Arena workflow could coexist. The legacy workflow has now been deleted; only Arena v1 is intended to schedule autonomous revenue cycles.
15. **Preflight caught a new syntax fault before execution.** Arena v1's first run failed because the reconciler file contained a newline escaping error. No Arena agent registration occurred on that failed preflight. The reconciler was corrected before the next run.

### Arena v1 controls

- Five independent lanes: sniper, research, creative, builder, premium.
- One registration per lane, then encrypted token reuse.
- Token vaults use OpenSSL AES-256-CBC + PBKDF2 and are stored only as encrypted artifacts/repository files.
- 100-job discovery per lane per cycle; up to five lanes and a 10-minute schedule give a theoretical ceiling of thousands of candidate evaluations over 12 hours without requiring duplicate bids on the same job.
- Each lane caps attempts per job at 3.
- Competitive cutoff by pending bid count.
- Price changes by competition density and lane mode.
- Wallet reconciliation before and after work.
- Hard 12-hour stop.
- $100 verified-revenue target gate.
- If the target is not met at the deadline, all five Arena lanes are marked retired in the competition ledger; if met, the board keeps the revenue leader and retires the others.
- Self-test and Python compilation run before any lane can register on Toku.

### Economic reality

Toku currently shows 280+ open jobs and 2,385+ agents. Several visible jobs have 100+ pending bids, so a raw-volume strategy alone is not a reliable conversion strategy. The Arena therefore prioritizes low-competition jobs and instant-accept opportunities instead of blindly bidding everywhere. citeturn826265search1turn826265search2turn826265search7
