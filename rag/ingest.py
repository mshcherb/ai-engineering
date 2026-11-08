"""Ingest the corpus: raw files -> clean, deduplicated, structure-aware chunks with metadata.

    python -m rag.ingest              # data/corpus/manifest.csv + raw/ -> chunks.jsonl, ingest_report.json

Pipeline (lesson 6, adapted to SEC filings and IR PDFs):
    extract blocks -> normalize -> document dedup (exact hash) -> version check (near-duplicates)
    -> chunk by sections -> chunk dedup (exact hash) -> metadata
"""
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import tiktoken

from rag.extract import extract

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
PIPELINE_VERSION = "ingest-v1"

# Chunk size: the embedding model (bge-small-en-v1.5) reads at most 512 of its own tokens, and its
# WordPiece tokenizer splits numbers harder than tiktoken, so we stay well below: target ~350.
MAX_TOKENS = 400
MIN_TOKENS = 60             # a smaller piece is merged with the next block of the same section
FIXED_TOKENS, FIXED_OVERLAP = 400, 50   # baseline for the comparison
NEAR_DUP_JACCARD = 0.5      # word 5-shingle overlap: "another version of the same document"

ENC = tiktoken.get_encoding("cl100k_base")


def n_tokens(text: str) -> int:
    return len(ENC.encode(text, disallowed_special=()))


# ---------------------------------------------------------------- normalize

def normalize(text: str) -> str:
    """One canonical form: NFKC (ligatures, full-width digits), no invisible characters, single spaces."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub("[​‌‍⁠﻿]", "", text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def doc_text(blocks: list[dict]) -> str:
    return "\n".join(b["text"] for b in blocks if b["type"] != "page")


def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- dedup / versions

def shingles(text: str, k: int = 5) -> set[int]:
    words = re.findall(r"\w+", text.casefold())
    return {hash(tuple(words[i:i + k])) for i in range(max(1, len(words) - k + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


# ---------------------------------------------------------------- chunking

def split_long_text(text: str, max_tokens: int) -> list[str]:
    """A paragraph longer than a chunk: cut between sentences."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(\"“])", text)
    parts, cur = [], ""
    for s in sentences:
        if cur and n_tokens(cur + " " + s) > max_tokens:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    # a single sentence longer than the limit (rare: run-on legal text) is cut by tokens
    out = []
    for p in parts:
        tokens = ENC.encode(p, disallowed_special=())
        out += [ENC.decode(tokens[i:i + max_tokens]) for i in range(0, len(tokens), max_tokens)]
    return out


def split_table(text: str, max_tokens: int) -> list[str]:
    """A table longer than a chunk: cut between rows and repeat the header in every piece."""
    lines = text.split("\n")
    header = lines[:2] if len(lines) > 1 and lines[1].startswith("| ---") else lines[:1]
    body = lines[len(header):]
    parts, cur = [], list(header)
    for row in body:
        if len(cur) > len(header) and n_tokens("\n".join(cur + [row])) > max_tokens:
            parts.append("\n".join(cur))
            cur = list(header)
        cur.append(row)
    parts.append("\n".join(cur))
    out = []
    for p in parts:  # a single row longer than a chunk (layout tables full of prose)
        out += split_long_text(p, max_tokens) if n_tokens(p) > max_tokens else [p]
    return out


def chunk_sections(blocks: list[dict], max_tokens: int = MAX_TOKENS) -> list[dict]:
    """Structure-aware chunks: a chunk never crosses a section boundary, never cuts a paragraph
    or a table row, and knows its section path ("Item 7. MD&A > Credit Quality") and page."""
    chunks: list[dict] = []
    path = ["", ""]               # level-1 heading (Item / part), level-2 heading
    page = None
    cur: list[str] = []
    cur_page = None

    def flush() -> None:
        nonlocal cur
        if cur:
            chunks.append({"text": "\n\n".join(cur), "section": " > ".join(p for p in path if p),
                           "page": cur_page})
            cur = []

    for b in blocks:
        if b["type"] == "page":
            page = b["number"]
            continue
        if b["type"] == "heading":
            # a new section starts a new chunk, unless what we have is too small to stand alone
            if cur and n_tokens("\n\n".join(cur)) >= MIN_TOKENS:
                flush()
            if b["level"] == 1:
                path = [b["text"], ""]
            else:
                path[1] = b["text"]
            continue
        pieces = (split_table(b["text"], max_tokens) if b["type"] == "table" else
                  split_long_text(b["text"], max_tokens) if n_tokens(b["text"]) > max_tokens else [b["text"]])
        for piece in pieces:
            if cur and n_tokens("\n\n".join(cur + [piece])) > max_tokens:
                flush()
            if not cur:
                cur_page = page
            cur.append(piece)
    flush()
    return chunks


def chunk_fixed(text: str, size: int = FIXED_TOKENS, overlap: int = FIXED_OVERLAP) -> list[dict]:
    """Baseline: a sliding window of tokens over the whole document."""
    tokens = ENC.encode(text, disallowed_special=())
    chunks, start = [], 0
    while start < len(tokens):
        chunks.append({"text": ENC.decode(tokens[start:start + size]), "section": "", "page": None})
        if start + size >= len(tokens):
            break
        start += size - overlap
    return chunks


def chunk_stats(chunks: list[dict]) -> dict:
    """How often a chunk starts mid-sentence or cuts a table row: the cost of naive chunking."""
    sizes = [n_tokens(c["text"]) for c in chunks] or [0]
    starts_mid = sum(1 for c in chunks if c["text"][:1].islower() or c["text"][:1] in ",;)")
    cut_rows = sum(1 for c in chunks
                   if any("|" in ln and not (ln.startswith("|") and ln.endswith("|"))
                          for ln in c["text"].split("\n")))
    with_section = sum(1 for c in chunks if c["section"])
    return {"chunks": len(chunks), "avg_tokens": round(sum(sizes) / len(sizes)), "max_tokens": max(sizes),
            "starts_mid_sentence_%": round(100 * starts_mid / len(chunks), 1),
            "cut_table_rows_%": round(100 * cut_rows / len(chunks), 1),
            "with_section_%": round(100 * with_section / len(chunks), 1)}


# ---------------------------------------------------------------- metadata

KIND_TITLE = {"annual": "annual report", "earnings": "quarterly earnings release",
              "management_report": "quarterly management report", "earnings_release": "quarterly earnings release",
              "presentation": "earnings presentation"}


def doc_title(doc: dict) -> str:
    return f"{doc['ticker']} {doc['form']} {KIND_TITLE.get(doc['kind'], doc['kind'])}, period {doc['period']}"


def mark_latest(docs: list[dict]) -> None:
    """Of several versions (same company, same kind of document), only the newest is current."""
    newest: dict[tuple, str] = {}
    for d in docs:
        key = (d["ticker"], d["kind"])
        newest[key] = max(newest.get(key, ""), d["period"])
    for d in docs:
        d["latest"] = d["period"] == newest[(d["ticker"], d["kind"])]


# ---------------------------------------------------------------- run

def main() -> None:
    with (CORPUS / "manifest.csv").open(encoding="utf-8") as f:
        docs = list(csv.DictReader(f))
    mark_latest(docs)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    report = {"pipeline_version": PIPELINE_VERSION, "documents": {}, "duplicates": [], "versions": [],
              "chunk_duplicates_removed": 0}
    texts, blocks_by_doc, seen = {}, {}, {}
    for d in docs:
        path = ROOT / d["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != d["sha256"]:
            raise SystemExit(f"{d['path']}: file differs from manifest.csv; re-run scripts/fetch_corpus.py")
        blocks = [{**b, "text": normalize(b["text"])} if "text" in b else b for b in extract(path)]
        blocks = [b for b in blocks if b["type"] == "page" or b["text"]]
        text = doc_text(blocks)
        d["doc_hash"] = content_hash(text)
        if d["doc_hash"] in seen:  # exact duplicate: same content under another name
            report["duplicates"].append({"doc": d["doc_id"], "same_as": seen[d["doc_hash"]]})
            d["status"] = "duplicate"
            continue
        seen[d["doc_hash"]] = d["doc_id"]
        d["status"] = "ok"
        texts[d["doc_id"]], blocks_by_doc[d["doc_id"]] = text, blocks
        print(f"  {d['doc_id']:38s} {len(text.split()):7d} words")

    # near-duplicates = versions of one document (10-K 2024 vs 2025): reported, both kept on purpose
    sh = {k: shingles(v) for k, v in texts.items()}
    for a, b in combinations(sh, 2):
        if a.split("_")[0] == b.split("_")[0]:  # only the same company can have versions
            score = jaccard(sh[a], sh[b])
            if score >= NEAR_DUP_JACCARD:
                report["versions"].append({"a": a, "b": b, "jaccard": round(score, 2)})

    all_chunks, fixed_all, seen_chunks = [], [], {}
    for d in sorted((d for d in docs if d["status"] == "ok"), key=lambda d: not d["latest"]):
        doc_id = d["doc_id"]
        chunks = chunk_sections(blocks_by_doc[doc_id])
        fixed_all += chunk_fixed(texts[doc_id])
        kept = 0
        for i, c in enumerate(chunks):
            h = content_hash(c["text"])
            if h in seen_chunks:  # boilerplate repeated in an older version: keep the newest copy only
                report["chunk_duplicates_removed"] += 1
                continue
            seen_chunks[h] = f"{doc_id}#{i}"
            kept += 1
            all_chunks.append({
                "chunk_id": f"{doc_id}#{i}", "doc_id": doc_id, "ticker": d["ticker"], "company": d["company"],
                "kind": d["kind"], "form": d["form"], "period": d["period"], "filed": d["filed"],
                "latest": d["latest"], "title": doc_title(d), "section": c["section"], "page": c["page"],
                "url": d["url"], "format": d["format"], "doc_hash": d["doc_hash"], "chunk_hash": h,
                "chunk_index": i, "n_tokens": n_tokens(c["text"]), "text": c["text"],
                "pipeline_version": PIPELINE_VERSION, "ingested_at": now,
            })
        report["documents"][doc_id] = {"words": len(texts[doc_id].split()), "chunks": kept,
                                       "latest": d["latest"], "doc_hash": d["doc_hash"]}

    report["chunking"] = {"sections": chunk_stats(all_chunks), "fixed": chunk_stats(fixed_all)}
    with (CORPUS / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (CORPUS / "ingest_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(all_chunks)} chunks from {len(report['documents'])} documents -> data/corpus/chunks.jsonl")
    print(json.dumps(report["chunking"], indent=2))
    print("versions:", report["versions"])


if __name__ == "__main__":
    main()
