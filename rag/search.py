"""Search over the chunks: vector, BM25, hybrid (RRF) and hybrid + reranking, with metadata filters.

    r = Retriever()
    hits = r.search("What was JPMorgan's CET1 ratio?", mode="hybrid+rerank",
                    filters={"ticker": ["JPM"], "latest": True}, k=5)

Based on the lesson 7/8 retriever, adapted to this corpus: chunk metadata filters instead of
access groups, a contextual header in both the vector and the BM25 text, reranking on top.
"""
import re
import time

import numpy as np
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import models
from rank_bm25 import BM25Okapi

from rag.index import (CHUNK_SETS, MODELS, build_collection, embed_chunks, embed_queries,
                       load_chunks, text_for_embedding)

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"   # ~80 MB cross-encoder, 512-token window
CANDIDATES = 30     # per list for RRF, and how many hybrid candidates the reranker sees
RRF_K = 60          # standard RRF constant: rank 1 -> 1/61, rank 30 -> 1/90
MODES = ("vector", "bm25", "hybrid", "hybrid+rerank")
STOPWORDS = set("the a an of and or in on for to what was is are were how did does do by with from at as its it".split())


def tokenize(text: str) -> list[str]:
    """Lower-case words and numbers; "$50.2" and "50.2%" keep their number, stopwords are dropped."""
    return [t for t in re.findall(r"[a-z]+|\d+(?:[.,]\d+)*", text.lower()) if t not in STOPWORDS]


def matches(chunk: dict, filters: dict | None) -> bool:
    """The same filters for BM25 (in Python) as for Qdrant (in the query)."""
    if not filters:
        return True
    if "ticker" in filters and chunk["ticker"] not in filters["ticker"]:
        return False
    if "kind" in filters and chunk["kind"] not in filters["kind"]:
        return False
    if filters.get("latest") and not chunk["latest"]:
        return False
    if "period_from" in filters and chunk["period"] < filters["period_from"]:
        return False
    if "period_to" in filters and chunk["period"] > filters["period_to"]:
        return False
    return True


def qdrant_filter(filters: dict | None) -> models.Filter | None:
    if not filters:
        return None
    must = []
    if "ticker" in filters:
        must.append(models.FieldCondition(key="ticker", match=models.MatchAny(any=filters["ticker"])))
    if "kind" in filters:
        must.append(models.FieldCondition(key="kind", match=models.MatchAny(any=filters["kind"])))
    if filters.get("latest"):
        must.append(models.FieldCondition(key="latest", match=models.MatchValue(value=True)))
    # period_from / period_to: ISO date strings, which Qdrant's numeric range does not compare;
    # they are applied in matches() after over-fetching candidates (see vector())
    return models.Filter(must=must) if must else None


class Retriever:
    def __init__(self, chunk_set: str = "sections"):
        self.chunks = load_chunks(chunk_set)
        vectors = embed_chunks(self.chunks, CHUNK_SETS[chunk_set][1])
        self.collection = f"corpus_{chunk_set}"
        self.client = build_collection(self.chunks, vectors, self.collection)
        self.bm25 = BM25Okapi([tokenize(text_for_embedding(c)) for c in self.chunks])
        self._reranker: TextCrossEncoder | None = None

    def vector(self, query: str, k: int, filters: dict | None = None) -> list[dict]:
        over = 5 if filters and ("period_from" in filters or "period_to" in filters) else 1
        hits = self.client.query_points(self.collection, query=embed_queries([query])[0], limit=k * over,
                                        query_filter=qdrant_filter(filters)).points
        found = [{**self.chunks[h.payload["idx"]], "cosine": h.score} for h in hits]
        return [c for c in found if matches(c, filters)][:k]

    def bm25_search(self, query: str, k: int, filters: dict | None = None) -> list[dict]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)
        out = []
        for i in order:
            if scores[i] <= 0 or len(out) == k:
                break
            if matches(self.chunks[i], filters):
                out.append({**self.chunks[i], "bm25": float(scores[i])})
        return out

    def hybrid(self, query: str, k: int, filters: dict | None = None) -> list[dict]:
        """Reciprocal rank fusion: a chunk high in either list (or in both) ends up on top."""
        scores: dict[str, float] = {}
        by_id: dict[str, dict] = {}
        for ranking in (self.vector(query, CANDIDATES, filters), self.bm25_search(query, CANDIDATES, filters)):
            for rank, hit in enumerate(ranking, 1):
                cid = hit["chunk_id"]
                scores[cid] = scores.get(cid, 0.0) + 1 / (RRF_K + rank)
                by_id[cid] = {**by_id.get(cid, {}), **hit}
        best = sorted(scores, key=lambda c: -scores[c])[:k]
        return [{**by_id[c], "rrf": scores[c]} for c in best]

    def rerank(self, query: str, candidates: list[dict], k: int) -> list[dict]:
        """A cross-encoder reads query and chunk together: slower, but sees which one actually answers."""
        if self._reranker is None:
            self._reranker = TextCrossEncoder(RERANK_MODEL, cache_dir=str(MODELS))
        if not candidates:
            return []
        scores = list(self._reranker.rerank(query, [text_for_embedding(c) for c in candidates]))
        order = sorted(range(len(candidates)), key=lambda i: -scores[i])[:k]
        return [{**candidates[i], "rerank": float(scores[i])} for i in order]

    def search(self, query: str, mode: str = "hybrid+rerank", filters: dict | None = None,
               k: int = 5) -> list[dict]:
        if mode == "vector":
            return self.vector(query, k, filters)
        if mode == "bm25":
            return self.bm25_search(query, k, filters)
        if mode == "hybrid":
            return self.hybrid(query, k, filters)
        if mode == "hybrid+rerank":
            return self.rerank(query, self.hybrid(query, CANDIDATES, filters), k)
        raise ValueError(f"unknown mode {mode!r}, expected one of {MODES}")


if __name__ == "__main__":
    import sys
    r = Retriever()
    q = " ".join(sys.argv[1:]) or "What was TSMC's gross margin in the third quarter of 2026?"
    for mode in MODES:
        t = time.perf_counter()
        hits = r.search(q, mode, k=3)
        print(f"\n== {mode} ({time.perf_counter() - t:.2f}s)")
        for h in hits:
            print(f"  {h['chunk_id']:40s} {h['section'][:60]}")
