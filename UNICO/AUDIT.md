# UNICO Audit — 2026-09-22

## Scope

This audit checks Toku, bid acceptance, jobs, delivery, wallet evidence, errors, competition, pricing, selection and service strategy. Revenue is counted only when a completed job is linked to a verified wallet/bank/Stripe credit or payout event. Leads, bids, contracts, escrow, receivables and pending work are excluded.

## Verified economic state

- Verified revenue: **USD 0.00**.
- Verified wallet/bank/Stripe balance: **not evidenced in repository; treated as USD 0.00**.
- Accepted jobs: **0 verified**.
- In-progress jobs: **0 verified**.
- Delivered jobs: **0 verified**.
- Completed jobs: **0 verified**.
- Revenue events: **none**.
- `REVENUE.csv`: header plus `NOT_COLLECTED`; no transaction rows.
- `runtime.json`: `engine=audit_only`, `status=BLOCKED_NO_VERIFIED_PLATFORM_OR_PAYOUT`, `collected_usd=0`, all verification-gate flags false.

No revenue advancement is declared.

## Ledger cross-check

- `REVENUE.csv` contains no qualifying transaction.
- `runtime.json` remains blocked and now includes explicit controlled-test parameters, but `enabled=false`.
- No repository evidence exists for a current Toku account identity, accepted job, delivery artifact, approval/settlement event, withdrawal, bank credit, Stripe credit, transaction hash or dated wallet balance.
- No lead, bid, contract, escrow amount, pending amount or platform-level balance has been counted as revenue.

## Toku and market evidence

Fresh public Toku evidence shows **305+ open jobs** and **2,650+ listed agents**. The platform advertises **85% auto-credit to the agent wallet on completion** and withdrawal through **Stripe Connect**. This is platform-level evidence, not account-level proof for UNICO. citeturn547531search0

Competition is severe. The current public homepage shows crowded jobs with roughly **120–169 bids** on several visible listings, including low-ticket work at **$3–$25**. This makes bid volume a poor optimization target and makes low-price creative positioning unattractive for a USD 5,000 target. citeturn547531search0

A third-party directory independently describes Toku as an 85% payout / Stripe model, but it is not account-level evidence and is not used to declare revenue. citeturn547531search1turn547531search6

## Errors and code risks

`UNICO/agent.py` still contains two dormant correctness defects that must be fixed before any live reactivation:

1. `handle_jobs()` calls `GET /agents/jobs?q=creative&status=OPEN&limit=100` without passing the agent token, while other authenticated calls do pass it. If Toku reactivates, job discovery may fail or behave as unauthenticated.
2. `inspect_setup_and_wallet()` sums every `JOB_EARNING` transaction and writes that total to `collected_usd`. This can overstate revenue if the endpoint includes pending, reversible, historical or non-settled earnings. Counting must require transaction-level settlement/credit evidence and reconciliation to `REVENUE.csv`.

Because `runtime.json` remains `audit_only` and blocked, neither defect produced external activity or revenue in this run.

## Pricing, selection and services

UNICO's service catalog is directionally aligned with Luca's real capabilities: creative campaign systems, short-form video strategy/editing blueprints, and music-release content packages.

However, the current Basic tiers at USD 15–25 are too low to support the target unless they are used only as deliberate reputation tests. The visible Toku market also contains many low-ticket agents and crowded $3–$25 jobs, so competing on price would create volume without enough net revenue. citeturn547531search0

The correct controlled-test posture is:

- minimum viable bid floor: **USD 75 gross**;
- at most **3 bids per cycle**;
- prefer Standard/Premium briefs with clear inputs, objective acceptance criteria and delivery in 24–48 hours;
- reject vague briefs, unpaid tests, jobs needing unauthorized credentials, and jobs with no visible payout path;
- do not delegate to other agents before UNICO has one verified incoming payout and wallet liquidity.

## Changes applied this run

1. Updated `UNICO/runtime.json` with controlled-test parameters: `min_bid_cents=7500`, `max_bids_per_cycle=3`, authenticated job discovery required, settled-credits-only wallet counting, and `no_reactivation_without_e2e_proof=true`.
2. Kept runtime economically unchanged at USD 0, wallet unverified and audit-only.
3. Kept `REVENUE.csv` unchanged because no qualifying payout exists.
4. Refreshed public Toku market evidence: 305+ open jobs, 2,650+ agents, 85% wallet credit / Stripe Connect payout claims, and visible high competition.
5. Did not enable Toku, publish services, bid, accept work or declare income.

## Required evidence for the next positive update

All evidence must refer to the same transaction:

1. Platform/account identity and payout rail.
2. Accepted job or signed order.
3. Delivery artifact and timestamp.
4. Client approval/completion or platform settlement.
5. Wallet/bank/Stripe credit evidence, preferably with transaction ID/hash or dated balance snapshot.

Until then:

- Verified revenue remains **USD 0.00**.
- Wallet remains **unverified**.
- No platform is declared active.

## Bottom line

UNICO has no verified income in the current ledgers. The highest-value optimization this run was to keep the system blocked, formalize controlled-test economics, lower exposure to crowded low-ticket bidding, and preserve strict settled-wallet accounting. No leads, bids, contracts, escrow, pending jobs or platform-level claims were counted as revenue.
