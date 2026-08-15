# RealStick Enterprise — Phase 1 Bootstrap

Production-oriented MVP foundation for the RealStick multi-outlet franchise management system.

## Stack
- React + TypeScript + Vite
- Tailwind CSS
- FastAPI
- Supabase PostgreSQL/Auth/Storage
- TanStack Query
- Axios

## Architecture
Browser -> React -> FastAPI -> Service/Repository -> Supabase PostgreSQL

Supabase Auth handles login/session/JWT. FastAPI validates JWTs and enforces role/franchise authorization from `public.profiles`.

The Supabase **service-role** key is server-only. The React app uses only the **anon** key.

## Setup

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Required backend env:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional backend env:
- `SUPABASE_JWT_SECRET` — unused for access-token verification (hosted project uses ES256 JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`)

### Frontend
```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Required frontend env:
- `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`)
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

### Database
Run `supabase/migrations/0001_initial_schema.sql` in the Supabase SQL Editor (already applied for this milestone).

### Auth users
Create users in the Supabase Auth dashboard, then insert matching rows into `public.profiles` (do not store passwords in profiles).

### Tests
```bash
cd backend
pytest
```

## Milestone status
1. Bootstrap — done
2. Database foundation — done (schema frozen for MVP)
3. Authentication foundation — in progress / complete in this branch

## Source baseline
The uploaded `RealStick_POS(1).html` prototype is the functional baseline. This repository replaces its localStorage persistence with a production API/database while preserving its business concepts.
