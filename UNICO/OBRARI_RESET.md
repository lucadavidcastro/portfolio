# UNICO — Autonomous Revenue Engine / Obrari

Reset: 2026-09-19
Target: USD 5,000 net received by 2026-11-09
Starting verified revenue: USD 0

## Retired
Toku/Arena is retired as primary execution. Human-only job-search targets are deleted from the operational pipeline.

## Platform
Obrari is the active target because it is explicitly built for autonomous AI agents: the agent bids, performs, delivers, and receives payout after approval. Jobs range from $10 to $500; the platform takes 10% plus Stripe processing, and approved payouts are released after a 48-hour dispute window.

## Strategy
Use four specialized agents, one per role:
1. Analyst — analysis/research/competitive reports. Target bids $150-$500.
2. Researcher — evidence synthesis, source-based briefs, market scans. Target $120-$450.
3. Writer — structured business writing, product copy, emails, documentation. Target $80-$350.
4. Data — spreadsheet cleanup, extraction, formatting, transformations. Target $80-$400.

Do not chase the $10-$50 floor. Reject work that is vague, unsafe, impossible to validate, or likely to require external browsing when the brief does not supply source material.

## Quality gate
New agents must pass Obrari benchmarks at >=60%. After 10+ jobs, keep approval rate >=70%. Prefer quality and approval rate over bid volume.

## Revenue math
Because payout is reduced by a 10% platform fee plus Stripe processing, USD 5,000 net requires more than USD 5,000 in gross approved work. Target gross booked/approved work: approximately USD 5,700-$6,000, depending on transaction mix.

## Manual blocker
The only user-side actions currently required are:
- create the Obrari account as an Agent Owner;
- connect the LLM provider/API key in Obrari;
- connect Stripe for payouts;
- pass the initial benchmark / put agents online.

These steps require identity/payment/account actions that are not exposed through the available tools.

No revenue is counted until Obrari/Stripe shows an actual payout or credited balance.
