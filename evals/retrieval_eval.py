"""Retrieval quality: recall@k and MRR for every query variant, search mode and both chunkings.

    python -m evals.retrieval_eval                 # all modes, section chunks + fixed-size baseline
    python -m evals.retrieval_eval --chunks sections

Query variants: the Russian question as is, rewritten into English by the LLM (rag/rewrite.py),
with and without the filters the LLM extracted, and the reference English wording, with and
without a ticker filter taken from the expected documents (an upper bound for the LLM filters).

A chunk counts as relevant if it comes from one of the expected documents and contains one of the
evidence strings of the question. Relevance is defined by text, not by chunk ids, so the same
questions work for any chunking.
"""
import argparse
import json
import re
import time
from pathlib import Path

from rag.rewrite import Rewriter
from rag.search import MODES, Retriever, matches

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


def gold_filters(q: dict) -> dict:
    return {"ticker": sorted({d.split("_")[0] for d in q["docs"]})}


def variants(questions: list[dict], rewrites: dict) -> dict:
    """Variant name -> function: question -> (query text, filters)."""
    return {
        "RU as is": lambda q: (q["question"], None),
        "RU→EN (LLM)": lambda q: (rewrites[q["id"]].query_en, None),
        "RU→EN + LLM filters": lambda q: (rewrites[q["id"]].query_en, rewrites[q["id"]].filters),
        "EN reference": lambda q: (q["question_en"], None),
        "EN + ticker filter": lambda q: (q["question_en"], gold_filters(q)),
    }


def evaluate(retriever: Retriever, questions: list[dict], mode: str, query) -> dict:
    """query: question -> (text to search with, metadata filters or None)."""
    hits5 = hits10 = 0
    rr_sum, latency, misses = 0.0, [], []
    for q in questions:
        text, filters = query(q)
        t = time.perf_counter()
        results = retriever.search(text, mode, filters, k=K)
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


def rewrite_report(questions: list[dict], rewrites: dict, chunks: list[dict]) -> dict:
    """How good the LLM filters are on their own: right tickers, and whether they keep the answer."""
    per_question = []
    for q in questions:
        rw = rewrites[q["id"]]
        relevant = [c for c in chunks if is_relevant(c, q)]
        per_question.append({
            "id": q["id"], "query_en": rw.query_en, "tickers": rw.tickers, "period": rw.period,
            "filters": rw.filters, "error": rw.error,
            "tickers_ok": rw.tickers == gold_filters(q)["ticker"],
            # False: the filters throw away every relevant chunk, no search mode can recover
            "keeps_answer": any(matches(c, rw.filters) for c in relevant),
        })
    costs = [rewrites[q["id"]].cost_usd for q in questions if rewrites[q["id"]].cost_usd is not None]
    return {"tickers_ok": sum(r["tickers_ok"] for r in per_question),
            "keeps_answer": sum(r["keeps_answer"] for r in per_question),
            "errors": sum(bool(r["error"]) for r in per_question),
            "cost_per_1000_usd": round(1000 * sum(costs) / len(costs), 3) if costs else None,
            "questions": per_question}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", nargs="*", default=["sections", "fixed"])
    args = parser.parse_args()
    # no_answer questions have no relevant chunk; they are scored on answers ("не знаю"), not on retrieval
    questions = [q for q in load_questions(QUESTIONS) if q["docs"]]
    rewriter = Rewriter()
    rewrites = {q["id"]: rewriter.rewrite(q["question"]) for q in questions}

    results, rewrite_stats = {}, None
    for chunk_set in args.chunks:
        retriever = Retriever(chunk_set)
        # a question whose evidence is in no chunk at all is a broken question, not a search miss
        unreachable = [q["id"] for q in questions if not any(is_relevant(c, q) for c in retriever.chunks)]
        if unreachable:
            print(f"[{chunk_set}] evidence not found in any chunk: {unreachable}")
        if chunk_set == "sections":
            rewrite_stats = rewrite_report(questions, rewrites, retriever.chunks)
            print(f"rewrite {rewriter.prompt_version}: tickers right {rewrite_stats['tickers_ok']}/{len(questions)}, "
                  f"filters keep the answer {rewrite_stats['keeps_answer']}/{len(questions)}, "
                  f"errors {rewrite_stats['errors']}")
        for variant, query in variants(questions, rewrites).items():
            for mode in MODES:
                name = f"{chunk_set} | {variant} | {mode}"
                results[name] = {**evaluate(retriever, questions, mode, query), "unreachable": unreachable}
                r = results[name]
                print(f"{name:55s} recall@5 {r['recall@5']:.2f}  recall@10 {r['recall@10']:.2f}  "
                      f"MRR {r['mrr@10']:.2f}  p50 {r['p50_s']}s", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "retrieval.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Retrieval: {len(questions)} questions, k = {K}\n",
             "| chunking | query | mode | recall@5 | recall@10 | MRR@10 | p50, s |", "|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        chunking, variant, mode = name.split(" | ")
        lines.append(f"| {chunking} | {variant} | {mode} | {r['recall@5']:.2f} | {r['recall@10']:.2f} "
                     f"| {r['mrr@10']:.2f} | {r['p50_s']} |")
    if rewrite_stats:
        (OUT / "rewrites.json").write_text(json.dumps(rewrite_stats, indent=2, ensure_ascii=False), encoding="utf-8")
        lines += [f"\n## Query rewriting ({rewriter.prompt_version}, {rewriter.run_cfg['model']})\n",
                  f"Tickers right: {rewrite_stats['tickers_ok']}/{len(questions)}; filters keep a relevant chunk: "
                  f"{rewrite_stats['keeps_answer']}/{len(questions)}; errors: {rewrite_stats['errors']}; "
                  f"cost per 1000 questions: ${rewrite_stats['cost_per_1000_usd']}\n",
                  "| id | query_en | tickers | filters | keeps answer |", "|---|---|---|---|---|"]
        for r in rewrite_stats["questions"]:
            filters = ", ".join(f"{k}={v}" for k, v in (r["filters"] or {}).items())
            lines.append(f"| {r['id']} | {r['query_en']} | {', '.join(r['tickers'])}{'' if r['tickers_ok'] else ' ✗'} "
                         f"| {filters} | {'yes' if r['keeps_answer'] else '**no**'} |")
    (OUT / "retrieval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"-> {(OUT / 'retrieval.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
