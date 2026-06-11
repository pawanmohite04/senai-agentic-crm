from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


JsonType = JSON().with_variant(JSONB, "postgresql")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="Active", index=True)
    account_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    churn_risk_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    threads = relationship("Thread", back_populates="contact")


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(500))
    sender_email: Mapped[str] = mapped_column(String(320), ForeignKey("contacts.email"), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255))

    contact = relationship("Contact", back_populates="threads")
    emails = relationship("Email", back_populates="thread", cascade="all, delete-orphan", order_by="Email.timestamp")


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_emails_message_id"),
        Index("ix_emails_sender_timestamp", "sender", "timestamp"),
        Index("ix_emails_category_urgency", "category", "urgency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("threads.id"), index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    sender: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0)
    category: Mapped[str] = mapped_column(String(50), default="Other", index=True)
    urgency: Mapped[str] = mapped_column(String(20), default="Low", index=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    priority_score: Mapped[float] = mapped_column(Float, default=0)
    raw_entities: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="Received", index=True)

    thread = relationship("Thread", back_populates="emails")
    actions = relationship("Action", back_populates="email", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_id: Mapped[int] = mapped_column(Integer, ForeignKey("emails.id"), index=True)
    agent_reasoning_log: Mapped[list | dict] = mapped_column(JsonType, default=list)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    proposed_content: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    email = relationship("Email", back_populates="actions")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_doc: Mapped[str] = mapped_column(String(255), index=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebIntelligenceCache(Base):
    __tablename__ = "web_intelligence_cache"
    __table_args__ = (Index("ix_web_cache_target_expiry", "target_entity", "expires_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    target_entity: Mapped[str] = mapped_column(String(255), index=True)
    scraped_data: Mapped[dict] = mapped_column(JsonType, default=dict)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(120))
    performed_by: Mapped[str] = mapped_column(String(255), default="agent")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    diff: Mapped[dict] = mapped_column(JsonType, default=dict)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    result: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
