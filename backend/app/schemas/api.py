from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class ErrorEnvelope(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = {}


class EmailIn(BaseModel):
    message_id: str = Field(min_length=1, max_length=255)
    sender: EmailStr
    subject: str = ""
    body: str = ""
    timestamp: datetime
    thread_id: str = Field(min_length=1, max_length=255)


class IngestResponse(BaseModel):
    job_id: str
    email_id: int
    duplicate: bool
    status: str
    priority_score: float


class ClassificationResult(BaseModel):
    category: str
    sentiment: str
    sentiment_score: float
    urgency: str
    requires_human: bool
    escalation_reason: str | None = None
    suggested_reply: str | None = None
    confidence: float
    detected_entities: dict[str, list[str]] = {}


class ContactOut(BaseModel):
    email: str
    name: str | None
    company: str | None
    status: str
    account_value: float
    churn_risk_score: float
    open_threads: int = 0


class StatusUpdate(BaseModel):
    status: Literal["VIP", "Blocked", "Active", "Churned"]


class DraftUpdate(BaseModel):
    proposed_content: str


class ReplyRequest(BaseModel):
    body: str
    approved_by: str = "user"
