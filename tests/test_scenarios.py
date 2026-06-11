import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def by_message(message_id: str) -> dict:
    data = json.loads(Path("email-data-advanced.json").read_text(encoding="utf-8"))
    return next(item for item in data if item["message_id"] == message_id)


def ingest(message_id: str) -> dict:
    return client.post("/api/ingest", json=by_message(message_id)).json()


def test_duplicate_ingestion_is_idempotent():
    first = ingest("msg_001")
    second = ingest("msg_001")
    assert second["duplicate"] is True
    assert first["email_id"] == second["email_id"]


def test_ransomware_never_auto_replies():
    result = ingest("msg_038")
    dry = client.post(f"/agent/dry-run/{result['email_id']}").json()
    assert "Security-Escalate" in dry["actions"]
    assert "Auto-Reply" not in dry["actions"]


def test_gdpr_is_compliance_not_generic_inquiry():
    result = ingest("msg_052")
    thread = client.get("/threads/marcus.del@fintech-startup.co").json()
    email = thread["threads"][0]["emails"][0]
    assert email["category"] == "Compliance"
    assert email["urgency"] == "Critical"
    assert email["requires_human"] is True
    assert "30-day" in email["actions"][0]["proposed_content"]


def test_legal_cease_and_desist_blocked():
    result = ingest("msg_020")
    response = client.post(f"/respond/{result['email_id']}", json={"body": "ok"})
    assert response.status_code == 409


def test_bob_msg_060_trace_has_required_steps():
    ingest("msg_002")
    ingest("msg_009")
    result = ingest("msg_060")
    dry = client.post(f"/agent/dry-run/{result['email_id']}").json()
    actions = [step["action"] for step in dry["trace"]]
    assert "get_thread_history" in actions
    assert "search_knowledge_base" in actions
    assert "check_account_status" in actions
    assert "Legal-Flag" in dry["actions"]


def test_alice_pricing_retrieves_pricing_policy():
    ingest("msg_001")
    ingest("msg_005")
    ingest("msg_014")
    ingest("msg_041")
    rag = client.get("/rag/search?q=pro-rata nonprofit Standard plan upgrade").json()
    assert rag["results"][0]["source_doc"] == "pricing_policy.md"


def test_karen_triggers_reputation_intelligence():
    ingest("msg_006")
    ingest("msg_018")
    result = ingest("msg_033")
    dry = client.post(f"/agent/dry-run/{result['email_id']}").json()
    assert any(step["action"] == "scrape_public_sentiment" for step in dry["trace"])


def test_nadia_bug_creates_ticket_action():
    result = ingest("msg_054")
    dry = client.post(f"/agent/dry-run/{result['email_id']}").json()
    assert "Ticket-Created" in dry["actions"]
