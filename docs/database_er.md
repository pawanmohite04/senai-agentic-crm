# Database ER Design

```mermaid
erDiagram
  CONTACTS ||--o{ THREADS : owns
  THREADS ||--o{ EMAILS : contains
  EMAILS ||--o{ ACTIONS : produces
  EMAILS ||--o{ AUDIT_LOG : audits
  KNOWLEDGE_CHUNKS ||--o{ ACTIONS : cites
  WEB_INTELLIGENCE_CACHE ||--o{ ACTIONS : enriches
```

Required tables are implemented in `backend/app/models/domain.py` and the first Alembic migration is `backend/alembic/versions/0001_initial_schema.py`.

Indexes:

- `emails(sender, timestamp)` supports full thread and sentiment trend queries.
- `emails(category, urgency)` supports dashboard filtering.
- `threads(thread_id)` supports idempotent thread linking.
- `web_intelligence_cache(target_entity, expires_at)` supports six-hour scrape caching.
- `audit_log(entity_type, entity_id)` supports entity history lookup.
