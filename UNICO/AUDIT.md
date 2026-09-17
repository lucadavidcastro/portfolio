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

