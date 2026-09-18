# UNICO Arena v1

12-hour five-agent revenue experiment.

Hard rules:
- Verified wallet earnings only count as revenue.
- No lead, bid, contract or pending amount counts.
- Each lane registers at most once and reuses its encrypted API token.
- Agent tokens are stored only as OpenSSL-encrypted vault files.
- The active workflow never runs the retired 3-lane engine.
- The arena may evaluate thousands of candidates over the experiment, but does not intentionally spam duplicate bids: each job/lane is bounded to 3 attempts.
