import hashlib
import math
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.domain import KnowledgeChunk


KB_DIR = Path(__file__).resolve().parents[3] / "knowledge_base"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9$.-]+", text.lower())


def embed_text(text: str, dims: int = 96) -> list[float]:
    vec = [0.0] * dims
    for token in tokenize(text):
        idx = int(hashlib.sha256(token.encode()).hexdigest(), 16) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def chunk_text(text: str, target_tokens: int = 420, overlap: int = 60) -> list[str]:
    words = text.split()
    if len(words) <= target_tokens:
        return [text.strip()]
    chunks = []
    start = 0
    while start < len(words):
        end = min(len(words), start + target_tokens)
        chunks.append(" ".join(words[start:end]).strip())
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def seed_knowledge_base(db: Session) -> int:
    count = 0
    for path in KB_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        existing = db.query(KnowledgeChunk).filter(KnowledgeChunk.source_doc == path.name).count()
        if existing:
            continue
        for chunk in chunk_text(text):
            db.add(KnowledgeChunk(source_doc=path.name, chunk_text=chunk, embedding=embed_text(chunk)))
            count += 1
    db.commit()
    return count


def search_knowledge_base(db: Session, query: str, limit: int = 3) -> list[dict]:
    if db.query(KnowledgeChunk).count() == 0:
        seed_knowledge_base(db)
    qvec = embed_text(query)
    query_tokens = set(tokenize(query))
    scored = []
    for chunk in db.query(KnowledgeChunk).all():
        score = cosine(qvec, chunk.embedding or [])
        doc = chunk.source_doc.lower()
        if "refund" in query_tokens and doc in {"refund_policy.md", "escalation_matrix.md"}:
            score += 0.35
        if {"sla", "outage", "downtime", "rca"} & query_tokens and doc == "sla_policy.md":
            score += 0.35
        if {"gdpr", "hipaa", "baa", "soc"} & query_tokens and doc == "compliance_faq.md":
            score += 0.35
        if {"legal", "ransomware", "security", "review"} & query_tokens and doc == "escalation_matrix.md":
            score += 0.3
        if {"pricing", "discount", "pro-rata", "upgrade"} & query_tokens and doc == "pricing_policy.md":
            score += 0.35
        scored.append({"id": chunk.id, "source_doc": chunk.source_doc, "chunk_text": chunk.chunk_text, "score": round(score, 4)})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
