# SenAI Agentic CRM Intelligence Platform

Production-oriented take-home submission for the SenAI Advanced Technical Assessment.

## What Is Included

- FastAPI backend with ingestion, deduplication, thread reconstruction, heuristic classification, structured LLM abstraction, RAG, autonomous triage agent, audit logs, contacts, analytics, and web intelligence.
- React/TypeScript/Vite dashboard with mission control inbox, thread workspace, reasoning traces, RAG context, web intelligence, and analytics.
- PostgreSQL schema via SQLAlchemy and Alembic, Docker Compose, seed scripts, simulator, KB documents, and tests.
- Full planning artifact in `docs/implementation_plan.md`.

## Dataset Analysis Note

The PDF says the dataset has 30 threads and describes Alice/Bob as 5/4 emails. The uploaded `email-data-advanced.json` has 60 emails across 47 distinct `thread_id`s; Alice has 4 emails and Bob outage has 3 outage-thread emails. The implementation uses the uploaded JSON as source of truth and also retrieves sender-level history for Bob.

## Quick Start

```bash
docker compose up --build
```

Then open:

- Backend Swagger: `http://localhost:8000/docs`
- Frontend dashboard: `http://localhost:5173`

Seed and replay:

```bash
docker compose exec backend python /scripts/email_simulator.py --file /email-data-advanced.json --base-url http://localhost:8000 --speed 10
```

Local backend without Docker:

```bash
cd backend
pip install -r requirements.txt
$env:PYTHONPATH="."
uvicorn app.main:app --reload
```

Then seed:

```bash
$env:PYTHONPATH="backend"
python scripts/seed_dataset.py
```

## Environment Variables

- `DATABASE_URL`: defaults to local SQLite; Docker uses PostgreSQL.
- `OPENAI_API_KEY`: optional. Without it, deterministic offline classification is used.
- `OPENAI_MODEL`: defaults to `gpt-5.5` per assessment recommendation and is configurable.
- `REDIS_URL`: Celery broker/backend.
- `OFFLINE_MODE`: keeps scraping and LLM behavior deterministic for evaluation.

## Safety Gates

The agent never auto-replies to:

- Spam
- Ransomware or data exfiltration threats
- Legal threats and cease-and-desist notices
- GDPR Article 20 requests
- Any Critical urgency email

The blocked cases still receive a proposed human-review draft when useful, with legal/security/compliance escalation.

## Key Scenario Behavior

- Bob `msg_060`: retrieves sender history, SLA policy, account renewal hold, legal flag, holding draft, escalation trace.
- Karen `msg_033`: detects repeated negative emails, reputation threat, refund/retention/escalation policies, web intelligence.
- GDPR `msg_052`: compliance/legal flag, 30-day statutory window draft, compliance ticket intent, no generic auto-reply.
- Ransomware `msg_038`: Critical security escalation, no attacker reply.
- Alice `msg_041`: pricing policy retrieves non-profit and pro-rata billing context.
- Nadia `msg_054`: Critical bug, engineering ticket, human escalation.
- Chatbot misinformation `msg_056`: refund policy retrieval, discrepancy acknowledgement, no liability admission.
- BigCorp and HIPAA: high-value enterprise/compliance routing.

## Trade-offs

- Chroma is included in Docker, while a deterministic SQL-backed vector fallback keeps tests portable and offline.
- The LLM adapter is interface-first. This avoids coupling safety tests to external model availability.
- Web intelligence uses cache and fixtures in offline mode so scraper failures do not block triage.
- Sender-level history is used in addition to `thread_id` because the dataset contains related Bob emails in separate threads.

## Verification

```bash
$env:PYTHONPATH="backend"
pytest
```

Generate OpenAPI:

```bash
$env:PYTHONPATH="backend"
python scripts/export_openapi.py
```
