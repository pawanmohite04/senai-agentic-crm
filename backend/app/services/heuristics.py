import html
import re
from dataclasses import dataclass


SPAM_PATTERNS = ["seo", "front page of google", "nigerian", "prince", "bank account", "processing fee", "limited offer", "coldoutreach"]
LEGAL_PATTERNS = ["cease and desist", "legal action", "legal team", "formal correspondence", "trademark", "gdpr article 20"]
SECURITY_PATTERNS = ["ransomware", "exfiltrated", "btc", "dark web", "suspicious login", "valid credentials", "data breach"]
REPUTATION_PATTERNS = ["twitter", "trustpilot", "g2", "capterra", "public review", "post publicly", "negative reviews"]
HIGH_VALUE_PATTERNS = ["rfp", "$2.4m", "200-seat", "enterprise", "hipaa", "baa", "board meets", "contract value"]
BUG_PATTERNS = ["bug", "crash", "500", "failing silently", "data missing", "success but", "not responding"]
COMPLIANCE_PATTERNS = ["hipaa", "baa", "soc 2", "gdpr", "data portability", "data residency", "iso 27001"]


@dataclass
class HeuristicResult:
    category: str
    urgency: str
    requires_human: bool
    priority_score: float
    confidence: float
    sentiment_score: float
    escalation_reason: str | None
    entities: dict
    status: str = "Received"


def normalize_text(subject: str | None, body: str | None) -> str:
    text = f"{subject or ''}\n{body or ''}"
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text: str, patterns: list[str]) -> bool:
    t = text.lower()
    return any(p in t for p in patterns)


def extract_entities(text: str) -> dict[str, list[str]]:
    return {
        "order_ids": re.findall(r"Order\s*#?(\d+)", text, flags=re.I),
        "ticket_ids": [
    a or b
    for a, b in re.findall(
        r"Ticket\s*#?(\d+)|PR\s*#?(\d+)",
        text,
        flags=re.I,
    )
],
        "monetary_amounts": re.findall(r"\$\s?[\d,]+(?:\.\d+)?|\d+\s?BTC", text, flags=re.I),
        "deadlines": re.findall(r"(?:Oct(?:ober)?\s+\d+|Dec(?:ember)?\s+\d+|within\s+\d+\s+(?:hours|days)|by\s+\w+)", text, flags=re.I),
        "products_mentioned": [p for p in ["API", "dashboard", "chatbot", "bulk upload", "webhook", "Standard", "Enterprise", "HIPAA"] if p.lower() in text.lower()],
    }


def classify_heuristic(sender: str, subject: str | None, body: str | None, sender_negative_count: int = 0) -> HeuristicResult:
    text = normalize_text(subject, body)
    lower = text.lower()
    domain = sender.split("@")[-1].lower()
    category = "Other"
    urgency = "Low"
    requires_human = False
    priority = 10.0
    confidence = 0.62
    sentiment = 0.0
    reason = None
    status = "Received"

    if not text:
        return HeuristicResult("Other", "Low", True, 20, 0.55, 0, "Empty or malformed content needs review", extract_entities(text))
    if len(text) > 10000:
        text = text[:10000]

    negative_words = ["unhappy", "angry", "worst", "unacceptable", "broken", "refund", "no reply", "legal", "crisis", "failing", "breach"]
    positive_words = ["love", "thanks", "resolved", "happy", "transformed", "proceed"]
    sentiment = min(1.0, 0.18 * sum(w in lower for w in positive_words)) - min(1.0, 0.22 * sum(w in lower for w in negative_words))

    if domain in {"internal.com", "mycompany.com"} or sender in {"ceo@company.com", "noreply@github.com"}:
        category, urgency, status, confidence = "Internal", "Low", "Ignored", 0.92
    elif contains_any(lower, SPAM_PATTERNS) or domain in {"marketing-guru.io", "wealth-transfer.com", "spammy-outreach.com"}:
        category, urgency, status, confidence = "Spam", "Low", "Ignored", 0.95
    elif contains_any(lower, SECURITY_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Legal" if "exfiltrated" in lower else "Other", "Critical", True, 100, 0.96
        reason = "Security incident or ransomware threat detected"
    elif "gdpr article 20" in lower or "data portability" in lower:
        category, urgency, requires_human, priority, confidence = "Compliance", "Critical", True, 95, 0.97
        reason = "Formal GDPR request with statutory handling requirements"
    elif contains_any(lower, LEGAL_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Legal", "Critical", True, 96, 0.95
        reason = "Legal threat or cease-and-desist language detected"
    elif contains_any(lower, COMPLIANCE_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Compliance", "High", True, 80, 0.9
        reason = "Compliance or regulated-enterprise request"
    elif contains_any(lower, BUG_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Bug Report", "High", True, 75, 0.86
        reason = "Bug or reliability issue requires support/engineering follow-up"
    elif "refund" in lower or "cancel" in lower or contains_any(lower, REPUTATION_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Complaint", "High", True, 78, 0.88
        reason = "Complaint, churn, refund, or public reputation risk"
    elif contains_any(lower, HIGH_VALUE_PATTERNS):
        category, urgency, requires_human, priority, confidence = "Compliance" if contains_any(lower, COMPLIANCE_PATTERNS) else "Inquiry", "High", True, 82, 0.84
        reason = "High-value enterprise opportunity"
    elif "pricing" in lower or "discount" in lower or "pro-rata" in lower or "upgrade" in lower:
        category, urgency, priority, confidence = "Billing", "Medium", 55, 0.83
    elif "feature" in lower or "roadmap" in lower:
        category, urgency, priority, confidence = "Feature Request", "Low", 35, 0.82
    elif "invoice" in lower or "billing" in lower or "subscription" in lower:
        category, urgency, priority, confidence = "Billing", "Medium", 50, 0.82
    else:
        category, urgency, priority = "Inquiry", "Medium", 40

    if "urgent" in lower or "p0" in lower or "mission-critical" in lower:
        urgency, priority, requires_human = "Critical", max(priority, 90), True
        reason = reason or "Critical urgency keywords detected"
    if sender_negative_count >= 2 and sentiment < 0:
        requires_human, priority, urgency = True, max(priority, 88), "High"
        reason = reason or "Sentiment deterioration: 3+ negative emails from sender"

    return HeuristicResult(category, urgency, requires_human, priority, confidence, sentiment, reason, extract_entities(text), status)
