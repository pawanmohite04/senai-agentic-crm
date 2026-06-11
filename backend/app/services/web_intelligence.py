from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.domain import WebIntelligenceCache


FIXTURES = {
    "reputation": {
        "g2": {"rating": 4.4, "recent_reviews": 3, "themes": ["slow support response", "refund friction"]},
        "trustpilot": {"rating": 3.9, "recent_reviews": 2, "themes": ["response time", "billing clarity"]},
        "competitors": [{"name": "CompetitorX", "rating": 4.6, "pricing_note": "Enterprise custom pricing"}],
    },
    "pricing": {
        "competitor_pricing": [{"name": "CompetitorX", "public_price": "$299/mo Pro", "enterprise": "custom"}]
    },
}


def should_fetch_intelligence(category: str, urgency: str, sentiment_score: float, text: str) -> bool:
    lower = text.lower()
    triggers = ["review", "trustpilot", "g2", "twitter", "post publicly", "press", "investor", "pricing"]
    return any(t in lower for t in triggers) or sentiment_score < -0.6 or (category == "Complaint" and urgency in {"High", "Critical"})


def get_reputation_summary(db: Session, target_entity: str = "ourplatform") -> dict:
    now = datetime.utcnow()
    cached = (
        db.query(WebIntelligenceCache)
        .filter(WebIntelligenceCache.target_entity == target_entity, WebIntelligenceCache.expires_at > now)
        .order_by(WebIntelligenceCache.scraped_at.desc())
        .first()
    )
    if cached:
        return cached.scraped_data
    data = {"robots_checked": True, "source": "offline-fixture", **FIXTURES["reputation"]}
    db.add(WebIntelligenceCache(
        source_url="fixture://g2-trustpilot",
        target_entity=target_entity,
        scraped_data=data,
        scraped_at=now,
        expires_at=now + timedelta(hours=6),
    ))
    db.commit()
    return data
