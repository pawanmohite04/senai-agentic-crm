# Architecture Design Justification

## FastAPI Backend

FastAPI was selected as the backend framework because it provides high-performance APIs, automatic OpenAPI documentation, strong type validation through Pydantic, and seamless integration with AI workflows. It serves as the central orchestration layer for email ingestion, classification, analytics, RAG retrieval, and autonomous agent operations.

## PostgreSQL Database

PostgreSQL is used as the primary system of record for storing emails, threads, contacts, classifications, analytics, and audit logs. A relational database is appropriate because email conversations, contacts, and thread relationships require structured querying and transactional consistency.

## Redis and Celery

Redis acts as the Celery broker and backend. Celery enables asynchronous processing of email intelligence workflows so that ingestion requests remain responsive while background tasks execute independently.

## ChromaDB and RAG

The assessment requires policy-aware and evidence-based reasoning. ChromaDB is used as the vector database for Retrieval-Augmented Generation (RAG). Internal knowledge base documents are embedded and retrieved during analysis, allowing the agent to ground decisions using company policies and operational guidelines.

A deterministic SQL-backed vector fallback is included to ensure portability and offline execution during evaluation.

## Heuristic Classification Layer

A deterministic heuristic engine performs the first stage of classification. It detects spam, security threats, compliance requests, complaints, billing issues, feature requests, and bug reports. This layer provides explainable and reliable classification before invoking higher-level reasoning.

## LLM Abstraction Layer

The platform uses a structured LLM abstraction layer. GPT-5.5 can be configured through environment variables, while an offline deterministic fallback guarantees functionality when no API key is available. This design avoids coupling core functionality to external model availability.

## Autonomous Triage Agent

The Autonomous Triage Agent combines classification results, thread history, sender history, RAG evidence, and policy rules to determine the appropriate action. The agent decides whether an email should be replied to automatically, escalated to a human, flagged for compliance review, or routed to security teams.

## Safety-First Automation

The platform intentionally prevents autonomous replies for high-risk scenarios including:

* Spam messages
* Security incidents
* Ransomware threats
* Legal notices
* GDPR requests
* Critical urgency emails

These scenarios require human oversight and escalation.

## Web Intelligence

Web Intelligence enriches customer context and reputation analysis. To maintain deterministic behavior during evaluation, cached fixtures and offline execution modes are used when external scraping is unavailable.

## Auditability and Explainability

Every significant decision can be traced through reasoning logs, RAG evidence, escalation records, and audit logs. This ensures transparency and supports enterprise governance requirements.

## React Mission Control Dashboard

The React + TypeScript + Vite frontend provides a unified Mission Control interface for reviewing customer threads, reasoning traces, RAG evidence, analytics, web intelligence, and escalation decisions. This enables operators to understand not only what decision was made but also why it was made.

## Key Trade-offs

* ChromaDB provides lightweight local RAG at the expense of enterprise-scale vector capabilities.
* The heuristic-first approach improves reliability and explainability but increases architectural complexity.
* Offline fallbacks improve portability but provide less intelligence than live LLM integrations.
* Safety-first automation reduces business risk while increasing the number of human escalations.

## Result

The final architecture satisfies the assessment requirements by providing email ingestion, thread reconstruction, intelligent classification, RAG-powered reasoning, autonomous triage, human escalation workflows, analytics, auditability, explainability, and production-ready deployment through Docker Compose.
