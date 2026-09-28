# Reviewer guide — Northline Care

This is the 10-minute path through the assessment.

## Start

```bash
git clone https://github.com/Sammy-t3ch/northline-returns.git
cd northline-returns
cp .env.example .env
# set NVIDIA_API_KEY=nvapi-...  (optional — policy still runs without it)
docker compose up --build
```

Open http://localhost:3000

Without a key, the engine still decides and a template reply is returned.
With a key, NVIDIA NIM drafts the customer-facing copy.

## What to look for

1. **Policy is not the model.** `backend/app/services/policy_engine.py` returns Approved / Denied / Escalated *before* `nvidia_ai.py` is called.
2. **The model cannot override.** System prompt + post-policy call order. Injection attempts escalate; they never approve.
3. **Scenarios are labeled.** Support tab chips include expected outcomes.
4. **Dates do not rot.** Orders use `days_ago` and are hydrated at load time, so the happy path stays inside 30 days.
5. **CI is green.** `.github/workflows/ci.yml` runs policy tests, API tests, and a frontend build.

## Click these seven chips

| Chip | Expected | Rule |
|------|----------|------|
| Happy path | Approved | In window, delivered, under $500 |
| Final sale | Denied | Entire cart is final sale |
| Too old | Denied | `days_ago` > 30 |
| Damage claim | Escalated | Evidence review |
| Over $500 | Escalated | Auto-approve cap |
| Still shipping | Escalated | Not delivered |
| Injection attempt | Escalated | Prompt-injection patterns |

Then open **Desk** and confirm the audit log shows reasons, not just labels.

## Tests without Docker

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. python tests_policy.py
PYTHONPATH=. pytest -q
```

## Design choice worth debating

NVIDIA is used **only** for reply generation. Letting the LLM classify refunds would demo the API more, but it would also be the wrong safety model for money movement. The assessment trades “more AI” for a decision you can unit-test.
