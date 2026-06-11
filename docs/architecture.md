# Architecture

See [implementation_plan.md](implementation_plan.md) for the requirement coverage matrix, Mermaid system architecture, ER design, API design, RAG architecture, agent architecture, web intelligence architecture, frontend dashboard design, folder structure, roadmap, and complete implementation plan.

## Runtime Flow

1. Simulator or API posts an email to `/api/ingest`.
2. The backend validates schema, deduplicates by `message_id`, links the thread, and runs a sub-10ms heuristic classifier.
3. RAG retrieves the top policy chunks and injects citations into classification/reply generation.
4. The autonomous agent runs a bounded tool loop and stores the full reasoning trace.
5. Safety gates block autonomous sends for spam, ransomware, legal threats, GDPR requests, and Critical urgency.
6. Dashboard reads the thread, RAG, reasoning, analytics, contact, and web-intelligence APIs.
