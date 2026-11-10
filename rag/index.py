"""Embeddings for the chunks, cached on disk, and the Qdrant collection built from them.

    python -m rag.index                  # embed new/changed chunks of data/corpus/chunks.jsonl
    python -m rag.index --chunks fixed   # same for the fixed-size baseline (for the comparison)

Embedding 10k chunks on a laptop CPU takes ~25 min, so vectors are cached by
sha256(model + embedded text): a re-run embeds only chunks that changed. The cache of the main
chunk set is committed (float16, ~7 MB), so CI and a fresh clone do not re-embed the corpus.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
MODELS = ROOT / ".models"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # 384 dims, 512-token window, English (the corpus is English)
CHUNK_SETS = {
    "sections": (CORPUS / "chunks.jsonl", CORPUS / "embeddings.npz"),               # committed
    "fixed": (CORPUS / "chunks_fixed.jsonl", ROOT / "data" / "index" / "embeddings_fixed.npz"),
}
# Payload fields Qdrant can filter on
FILTER_FIELDS = {"ticker": models.PayloadSchemaType.KEYWORD, "kind": models.PayloadSchemaType.KEYWORD,
                 "doc_id": models.PayloadSchemaType.KEYWORD, "latest": models.PayloadSchemaType.BOOL,
                 "period": models.PayloadSchemaType.KEYWORD}

_embedder: TextEmbedding | None = None


def load_chunks(chunk_set: str = "sections") -> list[dict]:
    path = CHUNK_SETS[chunk_set][0]
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def text_for_embedding(chunk: dict) -> str:
    """Contextual header: five banks write near-identical paragraphs, so the vector must also
    know whose document and which section the text comes from."""
    header = chunk["title"] + (f"\nSection: {chunk['section']}" if chunk["section"] else "")
    return f"{header}\n\n{chunk['text']}"


def cache_key(text: str) -> str:
    return hashlib.sha256(f"{EMBED_MODEL}\n{text}".encode("utf-8")).hexdigest()


def embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(EMBED_MODEL, cache_dir=str(MODELS))
    return _embedder


def embed_queries(queries: list[str]) -> np.ndarray:
    # bge models expect this instruction in front of a short query (not in front of passages)
    return np.array(list(embedder().query_embed(queries)), dtype=np.float32)


def embed_chunks(chunks: list[dict], cache_path: Path, log_every: int = 500) -> np.ndarray:
    """Vectors for all chunks; only those missing from the cache are computed."""
    cache: dict[str, np.ndarray] = {}
    if cache_path.exists():
        data = np.load(cache_path)
        cache = dict(zip(data["keys"], data["vectors"]))
    keys = [cache_key(text_for_embedding(c)) for c in chunks]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    if missing:
        print(f"embedding {len(missing)} of {len(chunks)} chunks with {EMBED_MODEL} ...")
        start = time.perf_counter()
        texts = (text_for_embedding(chunks[i]) for i in missing)
        for n, (i, vec) in enumerate(zip(missing, embedder().passage_embed(texts, batch_size=32)), 1):
            cache[keys[i]] = vec.astype(np.float16)
            if n % log_every == 0:
                rate = n / (time.perf_counter() - start)
                print(f"  {n}/{len(missing)}  {rate:.1f}/s  ~{(len(missing) - n) / rate / 60:.0f} min left", flush=True)
                save_cache(cache_path, cache, keys)  # keep progress if interrupted
        save_cache(cache_path, cache, keys)
    return np.array([cache[k] for k in keys], dtype=np.float32)


def save_cache(path: Path, cache: dict, keys: list[str]) -> None:
    """Store only vectors of current chunks, so the cache does not grow with every corpus change."""
    path.parent.mkdir(parents=True, exist_ok=True)
    live = [k for k in dict.fromkeys(keys) if k in cache]
    np.savez_compressed(path, keys=np.array(live), vectors=np.stack([cache[k] for k in live]))


def build_collection(chunks: list[dict], vectors: np.ndarray, name: str) -> QdrantClient:
    """In-process Qdrant: rebuilt from the cached vectors in seconds, nothing to run or deploy."""
    client = QdrantClient(":memory:")
    client.create_collection(name, vectors_config=models.VectorParams(
        size=vectors.shape[1], distance=models.Distance.COSINE))
    for field, schema in FILTER_FIELDS.items():
        client.create_payload_index(name, field, schema)
    payload = [{k: v for k, v in c.items() if k != "text"} | {"idx": i} for i, c in enumerate(chunks)]
    client.upload_collection(name, vectors=vectors, payload=payload, ids=list(range(len(chunks))))
    return client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="sections", choices=CHUNK_SETS)
    args = parser.parse_args()
    chunks = load_chunks(args.chunks)
    vectors = embed_chunks(chunks, CHUNK_SETS[args.chunks][1])
    print(f"{len(chunks)} chunks, vectors {vectors.shape} -> {CHUNK_SETS[args.chunks][1].relative_to(ROOT)}")


if __name__ == "__main__":
    main()
