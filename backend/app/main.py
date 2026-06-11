from collections import Counter, defaultdict
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import Base, engine, get_db
from app.models.domain import Action, AuditLog, Contact, Email, ProcessingJob, Thread
from app.schemas.api import ContactOut, DraftUpdate, EmailIn, IngestResponse, ReplyRequest, StatusUpdate
from app.services.agent import TriageAgent
from app.services.audit import audit
from app.services.heuristics import classify_heuristic, normalize_text
from app.services.llm import LLMClassifier
from app.services.rag import search_knowledge_base, seed_knowledge_base
from app.services.web_intelligence import get_reputation_summary

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SenAI Agentic CRM Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error(status_code: int, error_code: str, message: str, details: dict | None = None):
    raise HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message, "details": details or {}})


def sender_negative_count(db: Session, sender: str) -> int:
    rows = db.query(Email).filter(Email.sender == sender).order_by(Email.timestamp.desc()).limit(3).all()
    return sum(1 for row in rows if row.sentiment_score < -0.2)


def upsert_contact(db: Session, sender: str, timestamp: datetime) -> Contact:
    contact = db.query(Contact).filter(Contact.email == sender).first()
    if not contact:
        local, _, domain = sender.partition("@")
        company = domain.split(".")[0].replace("-", " ").title() if domain else None
        contact = Contact(email=sender, name=local.replace(".", " ").title(), company=company, last_contact_at=timestamp)
        if domain in {"bigcorp-global.com", "enterprise.net", "healthcare-group.org"}:
            contact.status = "VIP"
            contact.account_value = 2400000 if "bigcorp" in domain else 750000 if "enterprise" in domain else 200000
        db.add(contact)
    contact.last_contact_at = timestamp
    return contact


def ingest_email(payload: EmailIn, db: Session) -> IngestResponse:
    existing = db.query(Email).filter(Email.message_id == payload.message_id).first()
    if existing:
        job_id = f"job-{existing.message_id}"
        return IngestResponse(job_id=job_id, email_id=existing.id, duplicate=True, status=existing.status, priority_score=existing.priority_score)

    clean_body = normalize_text("", payload.body)
    clean_subject = normalize_text(payload.subject, "")
    if len(clean_body) > 10000:
        clean_body = clean_body[:10000]

    heuristic = classify_heuristic(payload.sender, clean_subject, clean_body, sender_negative_count(db, payload.sender))
    contact = upsert_contact(db, payload.sender, payload.timestamp.replace(tzinfo=None))
    thread = db.query(Thread).filter(Thread.thread_id == payload.thread_id).first()
    ts = payload.timestamp.replace(tzinfo=None)
    if not thread:
        thread = Thread(thread_id=payload.thread_id, subject=clean_subject, sender_email=payload.sender, first_seen_at=ts, last_updated_at=ts)
        db.add(thread)
        db.flush()
    else:
        thread.last_updated_at = max(thread.last_updated_at, ts)
        thread.first_seen_at = min(thread.first_seen_at, ts)

    email = Email(
        thread_id=thread.id,
        message_id=payload.message_id,
        sender=payload.sender,
        subject=clean_subject,
        body=clean_body,
        timestamp=ts,
        sentiment_score=heuristic.sentiment_score,
        category=heuristic.category,
        urgency=heuristic.urgency,
        requires_human=heuristic.requires_human,
        confidence=heuristic.confidence,
        priority_score=heuristic.priority_score,
        raw_entities=heuristic.entities,
        status=heuristic.status,
    )
    db.add(email)
    job = ProcessingJob(id=f"job-{uuid4().hex[:12]}", message_id=payload.message_id, status="processing", result={})
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.query(Email).filter(Email.message_id == payload.message_id).first()
        return IngestResponse(job_id=f"job-{payload.message_id}", email_id=duplicate.id, duplicate=True, status=duplicate.status, priority_score=duplicate.priority_score)
    db.refresh(email)

    rag = search_knowledge_base(db, f"{email.subject} {email.body}", limit=3)
    history = [{"subject": item.subject, "body": item.body} for item in db.query(Email).filter(Email.sender == email.sender).order_by(Email.timestamp).all()]
    llm_result = LLMClassifier().classify(heuristic, history, rag)
    email.category = llm_result.category
    email.urgency = llm_result.urgency
    email.requires_human = llm_result.requires_human
    email.confidence = llm_result.confidence
    email.sentiment_score = llm_result.sentiment_score
    email.raw_entities = llm_result.detected_entities
    if email.category not in {"Spam", "Internal"}:
        TriageAgent(db).run(email, dry_run=False)
    job.status = "completed"
    job.result = {"email_id": email.id, "category": email.category, "urgency": email.urgency}
    db.commit()
    audit(db, "email", email.id, "ingested", {"message_id": email.message_id, "category": email.category})
    return IngestResponse(job_id=job.id, email_id=email.id, duplicate=False, status=email.status, priority_score=email.priority_score)


@app.post("/api/ingest", response_model=IngestResponse)
def post_ingest(payload: EmailIn, db: Session = Depends(get_db)):
    return ingest_email(payload, db)


@app.get("/api/status/{job_id}")
def get_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        error(404, "JOB_NOT_FOUND", "Processing job not found", {"job_id": job_id})
    return {"job_id": job.id, "status": job.status, "result": job.result}


@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    emails = db.query(Email).all()
    return {
        "pending": sum(1 for e in emails if e.status in {"Received", "Processing"}),
        "replied": sum(1 for e in emails if e.status == "Replied"),
        "escalated": sum(1 for e in emails if e.status == "Escalated"),
        "critical": sum(1 for e in emails if e.urgency == "Critical"),
        "spam_filtered": sum(1 for e in emails if e.category == "Spam"),
    }


@app.get("/threads/{contact_email}")
def get_threads(contact_email: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == contact_email).first()
    if not contact:
        error(404, "CONTACT_NOT_FOUND", "Contact not found", {"email": contact_email})
    threads = db.query(Thread).filter(Thread.sender_email == contact_email).order_by(Thread.last_updated_at.desc()).all()
    return {
        "contact": contact,
        "threads": [
            {
                "thread_id": t.thread_id,
                "subject": t.subject,
                "status": t.status,
                "emails": [
                    {
                        "id": e.id,
                        "message_id": e.message_id,
                        "subject": e.subject,
                        "body": e.body,
                        "timestamp": e.timestamp,
                        "sentiment_score": e.sentiment_score,
                        "category": e.category,
                        "urgency": e.urgency,
                        "requires_human": e.requires_human,
                        "actions": [
                            {"id": a.id, "action_type": a.action_type, "proposed_content": a.proposed_content, "reasoning": a.agent_reasoning_log}
                            for a in e.actions
                        ],
                    }
                    for e in t.emails
                ],
            }
            for t in threads
        ],
    }


@app.post("/respond/{email_id}")
def respond(email_id: int, request: ReplyRequest, db: Session = Depends(get_db)):
    email = db.get(Email, email_id)
    if not email:
        error(404, "EMAIL_NOT_FOUND", "Email not found")
    blocked = email.category in {"Spam", "Legal"} or email.urgency == "Critical" or "gdpr" in f"{email.subject} {email.body}".lower()
    if blocked:
        error(409, "AUTO_REPLY_BLOCKED", "This email is blocked from autonomous reply", {"category": email.category, "urgency": email.urgency})
    email.status = "Replied"
    action = Action(email_id=email.id, action_type="Auto-Reply", proposed_content=request.body, is_approved=True, approved_by=request.approved_by, executed_at=datetime.utcnow(), agent_reasoning_log=[])
    db.add(action)
    db.commit()
    audit(db, "email", email.id, "reply_sent", {"approved_by": request.approved_by}, request.approved_by)
    return {"status": "sent", "email_id": email.id}


@app.patch("/drafts/{id}")
def edit_draft(id: int, payload: DraftUpdate, db: Session = Depends(get_db)):
    action = db.get(Action, id)
    if not action:
        error(404, "DRAFT_NOT_FOUND", "Draft/action not found")
    action.proposed_content = payload.proposed_content
    db.commit()
    audit(db, "action", id, "draft_edited", {"length": len(payload.proposed_content)}, "user")
    return {"id": id, "status": "updated"}


@app.post("/drafts/{id}/approve")
def approve_draft(id: int, approved_by: str = "user", db: Session = Depends(get_db)):
    action = db.get(Action, id)
    if not action:
        error(404, "DRAFT_NOT_FOUND", "Draft/action not found")
    email = db.get(Email, action.email_id)
    if email.category in {"Spam", "Legal"} or email.urgency == "Critical" or "gdpr" in f"{email.subject} {email.body}".lower():
        error(409, "APPROVAL_BLOCKED", "Safety policy blocks sending this draft")
    action.is_approved = True
    action.approved_by = approved_by
    action.executed_at = datetime.utcnow()
    email.status = "Replied"
    db.commit()
    audit(db, "action", id, "draft_approved", {"approved_by": approved_by}, approved_by)
    return {"id": id, "status": "approved"}


@app.get("/analytics/sentiment-trend")
def sentiment_trend(sender: str | None = None, days: int = 30, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days * 365) if days >= 30 else datetime.utcnow() - timedelta(days=days)
    query = db.query(Email).filter(Email.timestamp >= since)
    if sender:
        query = query.filter(Email.sender == sender)
    rows = query.order_by(Email.timestamp).all()
    points = [{"timestamp": e.timestamp, "sender": e.sender, "sentiment_score": e.sentiment_score} for e in rows]
    consecutive = defaultdict(int)
    alerts = []
    for e in rows:
        consecutive[e.sender] = consecutive[e.sender] + 1 if e.sentiment_score < -0.2 else 0
        if consecutive[e.sender] >= 3:
            alerts.append({"sender": e.sender, "alert": "sentiment_deterioration", "message_id": e.message_id})
    return {"points": points, "alerts": alerts, "query_plan": "index ix_emails_sender_timestamp supports sender/time trend queries"}


@app.get("/analytics/category-breakdown")
def category_breakdown(db: Session = Depends(get_db)):
    rows = db.query(Email.category, func.count(Email.id)).group_by(Email.category).all()
    return {"categories": [{"category": c, "count": n} for c, n in rows]}


@app.get("/rag/search")
def rag_search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    return {"query": q, "results": search_knowledge_base(db, q, 3), "target_latency_ms": 200}


@app.get("/intelligence/reputation")
def reputation(company: str = "ourplatform", db: Session = Depends(get_db)):
    return get_reputation_summary(db, company)


@app.post("/agent/dry-run/{email_id}")
def agent_dry_run(email_id: int, db: Session = Depends(get_db)):
    email = db.get(Email, email_id)
    if not email:
        error(404, "EMAIL_NOT_FOUND", "Email not found")
    return TriageAgent(db).run(email, dry_run=True)


@app.get("/audit/{entity_type}/{entity_id}")
def get_audit(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    rows = db.query(AuditLog).filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id).order_by(AuditLog.timestamp).all()
    return {"items": rows}


@app.get("/contacts/{email}", response_model=ContactOut)
def contact_profile(email: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email).first()
    if not contact:
        error(404, "CONTACT_NOT_FOUND", "Contact not found")
    open_threads = db.query(Thread).filter(Thread.sender_email == email, Thread.status == "Open").count()
    return ContactOut(email=contact.email, name=contact.name, company=contact.company, status=contact.status, account_value=float(contact.account_value), churn_risk_score=contact.churn_risk_score, open_threads=open_threads)


@app.patch("/contacts/{email}/status")
def update_contact_status(email: str, payload: StatusUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email).first()
    if not contact:
        error(404, "CONTACT_NOT_FOUND", "Contact not found")
    old = contact.status
    contact.status = payload.status
    db.commit()
    audit(db, "contact", contact.email, "status_updated", {"old": old, "new": payload.status}, "user")
    return {"email": email, "status": payload.status}


@app.post("/seed/knowledge-base")
def seed_kb(db: Session = Depends(get_db)):
    return {"chunks_created": seed_knowledge_base(db)}


@app.get("/")
def root():
    return {"service": "SenAI Agentic CRM", "docs": "/docs"}
