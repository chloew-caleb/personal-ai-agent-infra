"""Hybrid retrieval: exact-term search (SQLite FTS5) + semantic search (embeddings).

FTS5 is best for names, places, and rare words. Embeddings are best when the
wording differs from the stored text. New records are embedded incrementally.
"""
import sqlite3
import numpy as np

MODEL = "BAAI/bge-small-zh-v1.5"   # 512-d, works for Chinese and English
_model = None


def model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding   # lazy: loading the model is slow
        _model = TextEmbedding(MODEL)
    return _model


def embed(texts):
    v = np.array(list(model().embed(texts)), dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


class SemanticIndex:
    def __init__(self):
        self.ids = np.zeros(0, dtype=np.int64)
        self.vecs = np.zeros((0, 512), dtype=np.float32)

    def sync(self, conn: sqlite3.Connection, batch: int = 200) -> int:
        """Embed records that are not indexed yet."""
        known = set(self.ids.tolist())
        rows = [(i, t) for i, t in conn.execute(
            "SELECT id, content FROM memories WHERE is_deleted=0") if i not in known][:batch]
        if rows:
            self.ids = np.concatenate([self.ids, np.array([i for i, _ in rows], dtype=np.int64)])
            self.vecs = np.vstack([self.vecs, embed([t for _, t in rows])])
        return len(rows)

    def search(self, query: str, k: int = 5, min_score: float = 0.0):
        if not len(self.ids):
            return []
        scores = self.vecs @ embed([query])[0]          # cosine (vectors are normalised)
        top = np.argsort(-scores)[:k]
        return [(int(self.ids[i]), float(scores[i])) for i in top if scores[i] >= min_score]


def keyword_search(conn: sqlite3.Connection, query: str, k: int = 5):
    """Requires: CREATE VIRTUAL TABLE memories_fts USING fts5(content, content='memories', content_rowid='id')"""
    return [r[0] for r in conn.execute(
        "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?", (query, k))]


def hybrid(conn, index: SemanticIndex, query: str, k: int = 5):
    """Exact matches first, then semantic matches, de-duplicated."""
    seen, out = set(), []
    for i in keyword_search(conn, query, k) + [i for i, _ in index.search(query, k, min_score=0.6)]:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out[:k]
