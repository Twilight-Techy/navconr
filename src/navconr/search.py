from __future__ import annotations

from typing import Any, Protocol

from .models import IndexData, NavconrError
from .storage import Store
from .util import exact_slice, identity, terms

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "of",
    "to",
    "in",
    "for",
    "and",
    "what",
    "how",
    "does",
    "do",
    "which",
    "with",
    "where",
    "when",
    "it",
    "on",
    "can",
    "be",
    "we",
    "i",
    "s",
}


class Encoder(Protocol):
    fingerprint: str

    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceEncoder:
    def __init__(
        self, model: str = "sentence-transformers/all-MiniLM-L6-v2", revision: str | None = None
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise NavconrError("install navconr[embeddings] to use semantic embeddings") from exc
        self.fingerprint = identity(model, revision)
        self.model = SentenceTransformer(model, revision=revision)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


class Search:
    def __init__(self, store: Store, data: IndexData, encoder: Encoder | None = None):
        self.store, self.data, self.encoder = store, data, encoder
        self._vectors = None
        self._vectorizer: Any = None
        self._ids = [n.id for n in data.nodes.values() if n.kind == "block"]

    def text(self, nid: str) -> str:
        node = self.data.nodes[nid]
        return "\n".join(
            exact_slice(self.store.blob(s.blob), s.start, s.end)
            for sid in node.span_ids
            for s in [self.data.spans[sid]]
        )

    def lexical(self, query: str) -> list[tuple[str, float]]:
        keywords = [t for t in terms(query) if t not in STOPWORDS][:64]
        if not keywords:
            return []
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in keywords)
        table = self.store.search_table(self.data.revision)
        rows = self.store.db.execute(
            f"SELECT node,bm25({table}) AS score FROM {table} WHERE {table} MATCH ? ORDER BY score,node",
            (match,),
        ).fetchall()
        return [(nid, -float(score)) for nid, score in rows]

    def vector(self, query: str, semantic: bool = False) -> list[tuple[str, float]]:
        try:
            import numpy as np
        except ImportError as exc:
            raise NavconrError("install navconr[search] for vector search") from exc
        if not self._ids:
            return []
        if semantic:
            if not self.encoder:
                raise NavconrError("semantic search requires an explicit Encoder")
            vectors = []
            for nid in self._ids:
                text = self.text(nid)
                key = identity("embedding", self.encoder.fingerprint, text)
                cached = self.store.cache_get(key)
                vector = cached["vector"] if cached else self.encoder.encode([text])[0]
                if not cached:
                    self.store.cache_put(key, {"vector": vector})
                vectors.append(vector)
            matrix = np.asarray(vectors)
            q = np.asarray(self.encoder.encode([query])[0])
            norm = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q)
            scores = np.divide(matrix @ q, norm, out=np.zeros(len(matrix)), where=norm != 0)
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer

            if self._vectors is None:
                self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
                try:
                    self._vectors = self._vectorizer.fit_transform(
                        [self.text(nid) for nid in self._ids]
                    )
                except ValueError:
                    return []
            q = self._vectorizer.transform([query])
            scores = (self._vectors @ q.T).toarray().ravel()
        return sorted(
            [
                (nid, float(score))
                for nid, score in zip(self._ids, scores, strict=True)
                if score > 0
            ],
            key=lambda row: (-row[1], row[0]),
        )

    def rank(self, query: str, mode: str = "lexical") -> list[tuple[str, float]]:
        if mode == "lexical":
            return self.lexical(query)
        if mode in {"vector", "semantic"}:
            return self.vector(query, semantic=mode == "semantic")
        if mode == "hybrid":
            scores: dict[str, float] = {}
            for ranking in [self.lexical(query), self.vector(query)]:
                for i, (nid, _) in enumerate(ranking):
                    scores[nid] = scores.get(nid, 0) + 1 / (60 + i + 1)
            return sorted(scores.items(), key=lambda row: (-row[1], row[0]))
        raise NavconrError(f"unknown search mode: {mode}")
