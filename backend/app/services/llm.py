from app.schemas.api import ClassificationResult
from app.services.heuristics import HeuristicResult


class LLMClassifier:
    """Structured LLM classifier with deterministic offline fallback."""

    def classify(self, heuristic: HeuristicResult, thread_history: list[dict], rag_context: list[dict]) -> ClassificationResult:
        refs = ", ".join(sorted({c["source_doc"] for c in rag_context}))
        suggested = None
        if not heuristic.requires_human and heuristic.category not in {"Spam", "Internal"}:
            suggested = f"Thanks for reaching out. Based on {refs or 'our internal policy'}, here is the next step tailored to your request."
        return ClassificationResult(
            category=heuristic.category,
            sentiment=("Positive" if heuristic.sentiment_score > 0.2 else "Negative" if heuristic.sentiment_score < -0.2 else "Neutral"),
            sentiment_score=round(heuristic.sentiment_score, 3),
            urgency=heuristic.urgency,
            requires_human=heuristic.requires_human or heuristic.confidence < 0.70,
            escalation_reason=heuristic.escalation_reason if heuristic.requires_human or heuristic.confidence < 0.70 else None,
            suggested_reply=suggested,
            confidence=heuristic.confidence,
            detected_entities=heuristic.entities,
        )
