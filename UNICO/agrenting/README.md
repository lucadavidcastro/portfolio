# UNICO Agrenting Worker

This is the autonomous execution layer for UNICO.

## Required runtime secrets

- OPENAI_API_KEY
- AGRENTING_AGENT_API_KEY
- OPENAI_MODEL (optional; default gpt-5-mini)

## Public endpoints

- GET/HEAD /health
- POST /webhook/agrenting

The worker acknowledges dispatches immediately, deduplicates by dispatch_id, executes the scoped job with the provided Agrenting system prompt, and POSTs the result to the dispatch callback.

Do not commit secrets. Keep Agrenting owner credentials separate from the provider runtime key.

## Intended deployment

Run as a persistent HTTPS service (Replit Deployments or equivalent). Agrenting uses the callback URL for liveness and hiring dispatch. The public webhook must return 2xx to HEAD and accept HTTPS POST.
