"""Retrieval quality: recall@k and MRR for every search mode and both chunkings.

    python -m evals.retrieval_eval                 # all modes, section chunks + fixed-size baseline
    python -m evals.retrieval_eval --chunks sections

A chunk counts as relevant if it comes from one of the expected documents and contains one of the
evidence strings of the question. Relevance is defined by text, not by chunk ids, so the same
questions work for any chunking.
"""
import argparse
import json
import re
import time
from pathlib import Path

from rag.search import MODES, Retriever

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "evals" / "retrieval_questions.jsonl"
OUT = ROOT / "evals" / "results"
K = 10


def load_questions(path: Path) -> list[dict]:
    """JSON objects one after another: one per line (JSONL) or pretty-printed by an editor."""
    text, decoder, items, pos = path.read_text(encoding="utf-8"), json.JSONDecoder(), [], 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            return items
        obj, pos = decoder.raw_decode(text, pos)
        items.append(obj)


def norm(text: str) -> str:
    """'$ 18.68' and '$18.68', line breaks and case do not matter."""
    text = re.sub(r"\$\s+", "$", text.lower())
    return " ".join(text.split())


def is_relevant(chunk: dict, q: dict) -> bool:
    return chunk["doc_id"] in q["docs"] and any(norm(e) in norm(chunk["text"]) for e in q["evidence"])


def evaluate(retriever: Retriever, questions: list[dict], mode: str, use_filters: bool,
             field: str = "question_en") -> dict:
    """field: which wording to search with. "question_en" is the reference English wording;
    "question" is the Russian one (searched as is, or after the translation layer)."""
    hits5 = hits10 = 0
    rr_sum, latency, misses = 0.0, [], []
    for q in questions:
        filters = {"ticker": sorted({d.split("_")[0] for d in q["docs"]})} if use_filters else None
        t = time.perf_counter()
        results = retriever.search(q[field], mode, filters, k=K)
        latency.append(time.perf_counter() - t)
        rank = next((i for i, c in enumerate(results, 1) if is_relevant(c, q)), None)
        hits5 += bool(rank and rank <= 5)
        hits10 += bool(rank)
        rr_sum += 1 / rank if rank else 0.0
        if not rank or rank > 5:
            misses.append({"id": q["id"], "rank": rank, "top1": results[0]["chunk_id"] if results else None})
    n = len(questions)
    latency.sort()
    return {"recall@5": round(hits5 / n, 3), "recall@10": round(hits10 / n, 3), "mrr@10": round(rr_sum / n, 3),
            "p50_s": round(latency[n // 2], 2), "misses": misses}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", nargs="*", default=["sections", "fixed"])
    args = parser.parse_args()
    # no_answer questions have no relevant chunk; they are scored on answers ("не знаю"), not on retrieval
    questions = [q for q in load_questions(QUESTIONS) if q["docs"]]

    results = {}
    for chunk_set in args.chunks:
        retriever = Retriever(chunk_set)
        # a question whose evidence is in no chunk at all is a broken question, not a search miss
        unreachable = [q["id"] for q in questions if not any(is_relevant(c, q) for c in retriever.chunks)]
        if unreachable:
            print(f"[{chunk_set}] evidence not found in any chunk: {unreachable}")
        for mode in MODES:
            for use_filters in (False, True):
                name = f"{chunk_set} | {mode}{' + ticker filter' if use_filters else ''}"
                results[name] = {**evaluate(retriever, questions, mode, use_filters), "unreachable": unreachable}
                r = results[name]
                print(f"{name:45s} recall@5 {r['recall@5']:.2f}  recall@10 {r['recall@10']:.2f}  "
                      f"MRR {r['mrr@10']:.2f}  p50 {r['p50_s']}s", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "retrieval.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [f"# Retrieval: {len(questions)} questions, k = {K}\n",
             "| chunking | mode | recall@5 | recall@10 | MRR@10 | p50, s |", "|---|---|---|---|---|---|"]
    for name, r in results.items():
        chunking, mode = name.split(" | ")
        lines.append(f"| {chunking} | {mode} | {r['recall@5']:.2f} | {r['recall@10']:.2f} | {r['mrr@10']:.2f} | {r['p50_s']} |")
    (OUT / "retrieval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"-> {(OUT / 'retrieval.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
