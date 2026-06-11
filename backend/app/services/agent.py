from datetime import datetime

from sqlalchemy.orm import Session

from app.models.domain import Action, Email
from app.services.rag import search_knowledge_base
from app.services.web_intelligence import get_reputation_summary, should_fetch_intelligence


ENTERPRISE_STATUS = {
    "bob.jones@enterprise.net": {"tier": "Enterprise", "billing": "current", "renewal": "on hold", "account_value": 750000},
    "procurement@bigcorp-global.com": {"tier": "Prospect Enterprise", "billing": "n/a", "renewal": "rfp", "account_value": 2400000},
    "eleanor.voss@healthcare-group.org": {"tier": "Prospect Enterprise", "billing": "n/a", "renewal": "board decision", "account_value": 200000},
}


class TriageAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_thread_history(self, sender: str) -> list[dict]:
        emails = self.db.query(Email).filter(Email.sender == sender).order_by(Email.timestamp).all()
        return [{"message_id": e.message_id, "subject": e.subject, "body": e.body, "timestamp": e.timestamp.isoformat(), "category": e.category} for e in emails]

    def get_contact_profile(self, sender: str) -> dict:
        contact = self.db.query(Email).filter(Email.sender == sender).first()
        account = ENTERPRISE_STATUS.get(sender, {"tier": "Standard", "billing": "current", "renewal": "active", "account_value": 12000})
        return {"email": sender, "known": bool(contact), **account}

    def check_account_status(self, sender: str) -> dict:
        return ENTERPRISE_STATUS.get(sender, {"tier": "Standard", "billing": "current", "renewal": "active", "account_value": 12000})

    def draft_reply(self, email: Email, policy_refs: list[dict]) -> str:
        refs = ", ".join(sorted({r["source_doc"] for r in policy_refs}))
        if email.category == "Compliance" and "gdpr" in f"{email.subject} {email.body}".lower():
            return "We acknowledge receipt of your GDPR Article 20 portability request. Our compliance team will verify identity and coordinate the data export within the statutory 30-day window."
        if email.category == "Legal":
            return "We acknowledge receipt and are routing this to the appropriate leadership, legal, and security owners for review. A human owner will follow up through the appropriate channel."
        if "chatbot" in email.body.lower():
            return f"Thank you for flagging the discrepancy. We are reviewing the chatbot guidance against our current refund policy ({refs}) and will have a specialist follow up."
        return f"Thanks for the context. We reviewed the relevant policy references ({refs}) and are routing this to the right owner with the full thread context."

    def run(self, email: Email, dry_run: bool = False) -> dict:
        trace: list[dict] = []
        text = f"{email.subject}\n{email.body}"

        history = self.get_thread_history(email.sender)
        trace.append({"thought": "Need complete sender and thread context before acting.", "action": "get_thread_history", "observation": f"Retrieved {len(history)} emails for sender.", "next_step": "Search relevant knowledge base policies."})

        rag = search_knowledge_base(self.db, text, limit=3)
        trace.append({"thought": "Policy-grounded action is required.", "action": "search_knowledge_base", "observation": [r["source_doc"] for r in rag], "next_step": "Check contact/account risk."})

        account = self.check_account_status(email.sender)
        trace.append({"thought": "Account value and status affect escalation priority.", "action": "check_account_status", "observation": account, "next_step": "Determine legal/security/reputation gates."})

        actions: list[str] = []
        proposed = self.draft_reply(email, rag)
        lower = text.lower()
        if email.category == "Legal" or "legal" in lower or "cease and desist" in lower or "gdpr" in lower:
            actions.append("Legal-Flag")
            trace.append({"thought": "Legal or statutory language means no autonomous send.", "action": "flag_for_legal", "observation": "Legal/compliance queue flagged.", "next_step": "Escalate with brief."})
        if "ransomware" in lower or "exfiltrated" in lower or "btc" in lower or "suspicious login" in lower:
            actions.append("Security-Escalate")
            trace.append({"thought": "Security incident detected; attacker must not receive a reply.", "action": "escalate_to_human", "observation": "Security queue notified.", "next_step": "Stop before auto-reply."})
        if should_fetch_intelligence(email.category, email.urgency, email.sentiment_score, text):
            intel = get_reputation_summary(self.db)
            trace.append({"thought": "Reputation-sensitive context should include public signals.", "action": "scrape_public_sentiment", "observation": intel, "next_step": "Prepare human escalation brief."})
        if email.category == "Bug Report":
            actions.append("Ticket-Created")
            trace.append({"thought": "Reliability bug needs an engineering artifact.", "action": "create_internal_ticket", "observation": "Engineering ticket prepared.", "next_step": "Escalate to support owner."})

        safe_to_autoreply = email.urgency != "Critical" and email.category not in {"Spam", "Legal"} and "gdpr" not in lower and "ransomware" not in lower and "exfiltrated" not in lower
        if email.requires_human or not safe_to_autoreply:
            action_type = actions[0] if actions else "Escalate"
            actions.append("Escalate")
            trace.append({"thought": "Human review is required by policy or low safety margin.", "action": "escalate_to_human", "observation": "Escalation brief includes thread, RAG refs, and account status.", "next_step": "Store trace and proposed holding reply."})
        else:
            action_type = "Auto-Reply"
            actions.append("Auto-Reply")
            trace.append({"thought": "No safety gate blocks a grounded reply.", "action": "send_auto_reply", "observation": "Auto-reply eligible.", "next_step": "Store trace."})

        result = {"trace": trace[:6], "actions": actions, "proposed_content": proposed, "rag_context": rag}
        if not dry_run:
            self.db.add(Action(
                email_id=email.id,
                agent_reasoning_log=result,
                action_type=action_type,
                proposed_content=proposed,
                is_approved=False,
                executed_at=datetime.utcnow() if action_type == "Auto-Reply" else None,
            ))
            email.status = "Escalated" if "Escalate" in actions else "Replied"
            self.db.commit()
        return result
