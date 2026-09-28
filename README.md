# Northline Care — AI Refund System

Policy-gated customer support refund assistant for **Northline Care**.

- **Backend:** FastAPI · deterministic policy engine · NVIDIA NIM  
- **Frontend:** React (Vite) on **Cloudflare Pages**  
- **API host:** **Render** free tier (public HTTPS)  
- **Data:** Mock CRM with 16 orders  

> **Do not use localhost for demos.** Deploy the stack below so reviewers get a public URL.

---

## Public hosting (recommended)

### 1. Backend on Render (free)

1. Open the one-click blueprint (or connect the repo in the Render dashboard):

   **[Deploy to Render](https://render.com/deploy?repo=https://github.com/Sammy-t3ch/northline-returns)**

2. When prompted, set:

   | Variable | Value |
   |----------|--------|
   | `NVIDIA_API_KEY` | Your `nvapi-...` key |

3. After deploy, note the service URL, e.g.  
   `https://northline-returns-api.onrender.com`

4. Confirm health:  
   `https://northline-returns-api.onrender.com/api/health`

> Free tier sleeps after ~15 minutes idle. First request may take 30–60s (cold start).

### 2. Frontend on Cloudflare Pages (free)

1. Go to [Cloudflare Pages](https://dash.cloudflare.com/) → **Create** → **Connect to Git** → select `Sammy-t3ch/northline-returns`.
2. Build settings:

   | Setting | Value |
   |---------|--------|
   | Root directory | `frontend` |
   | Build command | `npm install && npm run build` |
   | Build output directory | `dist` |
   | Framework preset | Vite |

3. **Environment variables** (optional):

   | Name | Value |
   |------|--------|
   | `RENDER_API_URL` | `https://northline-returns-api.onrender.com` |

   (Pages Function at `functions/api/[[path]].js` proxies `/api/*` to Render.)

4. Deploy. Your public app URL will look like:  
   `https://northline-care-returns.pages.dev`

### 3. Share with reviewers

| What | URL |
|------|-----|
| **Live app** | `https://<your-pages-subdomain>.pages.dev` |
| **API docs** | `https://northline-returns-api.onrender.com/docs` |
| **Health** | `https://northline-returns-api.onrender.com/api/health` |

No localhost required.

---

## Architecture

```
Browser (Cloudflare Pages)
   │  /api/*  →  Pages Function proxy
   ▼
Render (FastAPI)
   ├─1. Policy engine (deterministic)
   ├─2. NVIDIA NIM (reply only)
   └─3. In-memory audit log
```

Policy always runs **before** the model. NVIDIA cannot approve a denied/escalated request.

---

## Local development (optional)

Only for your own machine — **not** for assessment submission links.

```bash
# Backend
cd backend && pip install -r requirements.txt
export NVIDIA_API_KEY=nvapi-...
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install
export VITE_API_URL=http://localhost:8000
npm run dev
```

Or: `docker compose up --build` (still local).

---

## Demo scenarios

| Scenario | Expected |
|----------|----------|
| Happy path (Maya / ORD-1001) | Approved |
| Final sale (Sofia / ORD-1003) | Denied |
| Too old (Liam / ORD-1004) | Denied |
| Damage claim (Carlos / ORD-1008) | Escalated |
| Injection attempt | Escalated |

---

## API

- `POST /api/refund` — `{ email, order_id?, message }`
- `GET /api/admin/requests`
- `GET /api/orders?email=`
- `GET /api/health`

---

## Repo

https://github.com/Sammy-t3ch/northline-returns
