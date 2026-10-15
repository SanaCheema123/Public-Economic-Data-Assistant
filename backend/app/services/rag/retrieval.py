from __future__ import annotations

import hashlib
import math
import re
from datetime import date
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.entities import Dataset, Indicator, RetrievalDocument, Source


STOPWORDS = {
    "what", "was", "is", "are", "the", "a", "an", "of", "in", "for", "to", "and", "or", "show", "me", "saudi", "arabia",
    "average", "latest", "current", "rate", "year", "years", "last", "over", "how", "has", "changed",
    "ما", "هو", "هي", "في", "من", "إلى", "على", "عن", "السعودية", "المملكة", "العربية", "خلال", "آخر", "اخر", "سنة", "سنوات", "معدل", "اعرض", "أرني",
}

def _tokens(text_value: str) -> set[str]:
    text_value = re.sub(r"[^\w\u0600-\u06FF]+", " ", text_value.lower())
    return {token for token in text_value.split() if len(token) > 1 and token not in STOPWORDS and not token.isdigit()}


def _embedding(text_value: str, dims: int = 384) -> list[float]:
    vec = [0.0] * dims
    for token in _tokens(text_value):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dims
        vec[idx] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@dataclass
class RetrievedIndicator:
    indicator: Indicator
    dataset: Dataset
    source: Source
    score: float


class RAGRetriever:
    def retrieve_indicators(self, db: Session, question: str, limit: int = 5) -> list[RetrievedIndicator]:
        vector_results = self._pgvector_search(db, question, limit)
        if vector_results:
            return vector_results
        q_tokens = _tokens(question)
        docs = db.scalars(select(RetrievalDocument).where(RetrievalDocument.kind == "indicator")).all()
        scored: list[tuple[float, RetrievalDocument]] = []
        for doc in docs:
            keyword_tokens = _tokens(" ".join(str(k) for k in (doc.keywords or [])))
            name_tokens = _tokens(doc.title_en + " " + doc.title_ar)
            doc_tokens = _tokens(" ".join([doc.title_en, doc.title_ar, doc.content_en, doc.content_ar])) | keyword_tokens
            overlap = len(q_tokens & doc_tokens)
            keyword_overlap = len(q_tokens & keyword_tokens)
            name_overlap = len(q_tokens & name_tokens)
            coverage = overlap / max(1, len(q_tokens))
            score = coverage * 0.45 + keyword_overlap * 0.35 + name_overlap * 0.30
            if score >= 0.28:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        output: list[RetrievedIndicator] = []
        for score, doc in scored[: max(limit * 3, limit)]:
            indicator = db.get(Indicator, doc.ref_id)
            if not indicator:
                continue
            dataset = db.get(Dataset, indicator.dataset_id)
            source = db.get(Source, indicator.source_id)
            if dataset and source and indicator.verification_status == "verified" and dataset.verification_status == "verified":
                adjusted = self._rerank_score(question, source, indicator, score)
                output.append(RetrievedIndicator(indicator, dataset, source, round(adjusted, 4)))
        output.sort(key=lambda item: item.score, reverse=True)
        return output[:limit]

    def _pgvector_search(self, db: Session, question: str, limit: int) -> list[RetrievedIndicator]:
        if not db.bind or db.bind.dialect.name != "postgresql":
            return []
        vector = _embedding(question)
        vec_literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
        try:
            rows = db.execute(text("""
                SELECT ref_id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM retrieval_documents
                WHERE kind = 'indicator' AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """), {"embedding": vec_literal, "limit": limit}).mappings().all()
        except Exception:
            db.rollback()
            return []
        output: list[RetrievedIndicator] = []
        for row in rows:
            indicator = db.get(Indicator, row["ref_id"])
            if not indicator:
                continue
            dataset = db.get(Dataset, indicator.dataset_id)
            source = db.get(Source, indicator.source_id)
            if dataset and source and indicator.verification_status == "verified" and dataset.verification_status == "verified":
                adjusted = self._rerank_score(question, source, indicator, float(row["score"] or 0))
                output.append(RetrievedIndicator(indicator, dataset, source, adjusted))
        output.sort(key=lambda item: item.score, reverse=True)
        return output[:limit]

    @staticmethod
    def _rerank_score(question: str, source: Source, indicator: Indicator, score: float) -> float:
        lowered = question.lower()
        year_match = re.search(r"\b(?:19|20)\d{2}\b", question)
        explicit_year = bool(year_match)
        requested_year = int(year_match.group(0)) if year_match else None
        timeseries = any(x in lowered for x in ["trend", "over time", "last ", "history", "historical"]) or any(x in question for x in ["خلال", "اتجاه", "سنوات", "تاريخي"])
        latest_terms = any(x in lowered for x in ["latest", "current", "today", "now", "most recent"]) or any(x in question for x in ["أحدث", "الاحدث", "الحالي", "الحالية", "الآن", "الان"])
        latest_style = latest_terms or (not explicit_year and not timeseries)
        if (latest_style or requested_year == date.today().year) and source.slug == "gastat" and indicator.indicator_id.startswith("GASTAT."):
            return score + 0.55
        if timeseries and source.slug == "world-bank":
            return score + 0.18
        return score

    def retrieve_sources(self, db: Session, indicator: Indicator) -> list[Source]:
        source = db.get(Source, indicator.source_id)
        return [source] if source else []

    def retrieve_definition(self, indicator: Indicator, language: str) -> str:
        return indicator.description_ar if language == "ar" else indicator.description_en


retriever = RAGRetriever()
