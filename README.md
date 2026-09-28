# Northline Care — AI Refund System

Policy-gated customer support refund assistant for the **Northline Care** brand assessment.

- **Backend:** FastAPI + deterministic policy engine + NVIDIA NIM (Llama 3.1)
- **Frontend:** React (Vite) — customer chat, support desk, policy view
- **Data:** Mock CRM with 15+ orders in JSON
- **Ops:** `docker-compose up` for full stack

## Quick start (Docker)

```bash
cp .env.example .env
# Put your NVIDIA API key in .env:
# NVIDIA_API_KEY=nvapi-...

docker compose up --build
```

| Service  | URL                    |
|----------|------------------------|
| Frontend | http://localhost:3000  |
| API docs | http://localhost:8000/docs |
| Health   | http://localhost:8000/api/health |

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export NVIDIA_API_KEY=nvapi-...
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
export VITE_API_URL=http://localhost:8000
npm run dev
```

## Environment variables

| Variable         | Required | Description                                      |
|------------------|----------|--------------------------------------------------|
| `NVIDIA_API_KEY` | Yes*     | NVIDIA NIM / integrate.api.nvidia.com key        |
| `NVIDIA_MODEL`   | No       | Default `meta/llama-3.1-70b-instruct`             |

*If the key is missing, the API still works: policy decisions are computed in code and a template reply is returned.

## Architecture

```
Customer UI ──POST /api/refund──► FastAPI
                                   │
                                   ├─1. Policy engine (deterministic)
                                   │     • age ≤ 30 days
                                   │     • final-sale check
                                   │     • $500 high-value → Escalate
                                   │     • damage keywords → Escalate
                                   │     • injection patterns → Escalate
                                   │
                                   ├─2. NVIDIA NIM (reply only)
                                   │     • cannot override policy decision
                                   │
                                   └─3. In-memory audit log → Desk UI
```

### Why policy runs before the LLM

Hard rules live in Python (`app/services/policy_engine.py`). The model only receives the already-decided outcome and drafts a brand-appropriate message.

### AI integration

- OpenAI-compatible client pointed at `https://integrate.api.nvidia.com/v1`
- System prompt forbids changing the decision or revealing internal rules
- Fallback templates if the NVIDIA call fails

## Demo scenarios (Support tab)

| Scenario          | Expected   |
|-------------------|------------|
| Happy path        | Approved   |
| Final sale        | Denied     |
| Too old           | Denied     |
| Damage claim      | Escalated  |
| Injection attempt | Escalated  |

## API surface

- `POST /api/refund` — process a refund request
- `GET /api/admin/requests` — recent decisions for the Desk
- `GET /api/orders?email=` — inspect mock CRM
- `GET /api/health`

## Assumptions & trade-offs

- Mock data is static JSON; swap for SQLite/Postgres if needed.
- Audit log is in-memory (resets on restart) — sufficient for the assessment demo.
- Demo “today” is fixed at 2026-09-28 so age checks stay reproducible.
- No auth on the Desk endpoint (assessment scope).

## Brand

**Northline Care** — apparel & outdoor gear. UI uses a calm editorial palette (cream / forest green).
