# Voice-Clone Shield — v1 MVP scaffold

AI voice-clone protection for independent musicians. An artist enrolls a **voiceprint**
(a 192-dim ECAPA-TDNN speaker embedding of their voice), uploads any suspect clip, and gets
a cosine-similarity match report plus a downloadable **evidence-pack PDF** for takedown filings.

India-first positioning: affordable pilot pricing (₹299–999/mo in the roadmap),
Reels/YouTube focus, IT Rules takedown workflow. The closest incumbent (Vermillio, $100/mo)
serves Western celebrities/labels — this is the creator-side alternative.

> **v1 is manual-upload matching only.** Automated scanning of YouTube/Instagram/Reels,
> the "license my voice" marketplace, and per-artist adaptive thresholds are stubbed for v2.

## Architecture

```
voice-clone-shield/
├── backend/                 FastAPI + SQLAlchemy + pgvector
│   ├── app/
│   │   ├── main.py          app factory, CORS, startup checks
│   │   ├── config.py        env-only config (no secrets in code)
│   │   ├── database.py      engine, session, pgvector bootstrap
│   │   ├── models.py        User / Voiceprint / MatchCheck
│   │   ├── schemas.py       Pydantic v2 request/response models
│   │   ├── security.py      PBKDF2 password hashing + JWT (PyJWT)
│   │   ├── audio.py         load → energy VAD → ECAPA-TDNN embedding (CPU)
│   │   ├── evidence.py      evidence-pack PDF (fpdf2)
│   │   └── routers/         auth.py, voiceprints.py, checks.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/                React 18 + Vite (original hand-rolled UI, no UI framework)
│   └── src/                 App.jsx (auth, dashboard, enroll, check, history), api.js, styles.css
├── docker-compose.yml       Postgres 16 + pgvector for local dev
└── README.md
```

## Prerequisites

- Python 3.11+ · Node 18+ · Postgres 15+ with the `pgvector` extension
  (or Docker — `docker compose up -d` gives you exactly that)
- System lib for audio decoding: `libsndfile1` (`sudo apt install libsndfile1`)
- The speaker model (`speechbrain/spkrec-ecapa-voxceleb`) downloads automatically
  from Hugging Face on first enrollment/check (~100 MB, cached in `~/.cache`).

## Quickstart

**1. Database**
```bash
docker compose up -d
# or point DATABASE_URL at your own Postgres with pgvector installed
```

**2. Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# CPU-only torch (avoids the giant CUDA wheels):
pip install torch --index-url https://download.pytorch.org/whl/cpu
cp .env.example .env
# edit .env -> set JWT_SECRET, e.g.  openssl rand -hex 32
uvicorn app.main:app --reload --port 8000
```
Tables + the `vector` extension are created automatically on startup.

**3. Frontend**
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api -> :8000)
```

**Demo flow:** sign up → *Enroll voice* (upload 2–3 min of clean vocals) →
*Check a clip* (upload a suspect clip) → verdict + scores → *Download evidence PDF* →
confirm/reject feedback.

## API summary

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | – | `{email, artist_name, password}` → JWT |
| POST | `/api/auth/login` | – | `{email, password}` → JWT |
| GET | `/api/auth/me` | Bearer | Current artist |
| POST | `/api/voiceprints` | Bearer | `label` + audio file → voiceprint |
| GET | `/api/voiceprints` | Bearer | List enrolled voiceprints |
| DELETE | `/api/voiceprints/{id}` | Bearer | Delete voiceprint |
| POST | `/api/checks` | Bearer | audio file (+ optional `voiceprint_id`) → ranked matches |
| GET | `/api/checks` | Bearer | Check history |
| GET | `/api/checks/{id}` | Bearer | One check |
| POST | `/api/checks/{id}/feedback` | Bearer | `{verdict: confirmed\|rejected, note?}` |
| GET | `/api/checks/{id}/evidence` | Bearer | Evidence-pack PDF download |

## How matching works

1. Audio → mono 16 kHz, peak-normalised (`soundfile` + `scipy`).
2. Energy-based VAD gates silence/instrumental beds; clips with <10% voiced audio are rejected.
3. Voiced audio is embedded with ECAPA-TDNN in 30 s chunks, averaged, L2-normalised.
4. Cosine similarity vs each enrolled voiceprint (stored as `vector(192)` in pgvector).
5. Bands: `≥ MATCH_THRESHOLD` (default 0.70) → likely match; `≥ REVIEW_THRESHOLD`
   (default 0.55) → review; else no match. Thresholds are env-configurable.

Deliberately **not** audio fingerprinting: fingerprints match *recordings*, not voices —
an AI clone singing a brand-new song would never hit a fingerprint database.

## Configuration (env vars)

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://shield:shield@localhost:5432/shield` | must have pgvector |
| `JWT_SECRET` | *(required)* | `openssl rand -hex 32`; boot fails without it |
| `ACCESS_TOKEN_MINUTES` | `1440` | |
| `STORAGE_DIR` | `./storage` | local audio storage (v1) |
| `MATCH_THRESHOLD` / `REVIEW_THRESHOLD` | `0.70` / `0.55` | cosine similarity bands |
| `MAX_UPLOAD_MB` | `50` | |

## v1 scope vs v2 stubs

**In v1:** signup/login (JWT), voiceprint enrollment, manual suspect-clip checks,
dashboard + history, confirm/reject feedback loop, evidence-pack PDF.

**Stubbed for v2 (not implemented):**
- Automated scanning of YouTube / Instagram Reels / ShareChat / Moj (v1 compares
  uploads you provide; no scraping, no platform APIs).
- Per-artist adaptive thresholds learned from the feedback loop (feedback is
  *recorded* in v1; thresholds are still global env vars).
- "License my voice" consent marketplace (Grimes/Holly+ style).
- IT Rules / DMCA one-click takedown filing (v1 gives you the evidence PDF to attach).
- Background job queue (Celery/SQS) — v1 processes uploads synchronously in the request.
- S3 storage — v1 uses local disk (`STORAGE_DIR`).

## Security notes

- No secrets in code: `JWT_SECRET` and `DATABASE_URL` are env-only; the app refuses
  to boot with the placeholder secret.
- Passwords: PBKDF2-HMAC-SHA256, 260k iterations, per-user salt (stdlib only).
- Uploads are size-capped, extension-validated, and namespaced per user on disk.
