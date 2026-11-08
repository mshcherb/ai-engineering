"""Answer quality on the testset: deterministic scores (source, key facts, "не знаю").

    python -m evals.answer_eval              # 29 questions through RAG -> evals/results/answers.{jsonl,md,json}
    python -m evals.answer_eval --rescore    # score the saved answers again, no model calls

Scores of one answer (None when the score does not apply to the case):
    source         an expected document among the cited chunks
    facts          every `must` number is in the answer, compared by value (evals/scoring.py)
    abstain        no_answer case: the bot said "не знаю"
    false_abstain  answerable case: the bot said "не знаю" anyway
    pass           answerable: found, source and facts; no_answer: abstain
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from evals.scoring import fact_found
from evals.testset import load_testset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evals" / "results"
ANSWERS = OUT / "answers.jsonl"
METRICS = ["pass", "source", "facts", "abstain", "false_abstain"]


def doc_of(chunk_id: str) -> str:
    return chunk_id.split("#")[0]


def score(r: dict, case: dict) -> dict:
    if case["type"] == "no_answer":
        abstain = not r["found"]
        return {"source": None, "facts": None, "abstain": abstain, "false_abstain": None, "pass": abstain}
    source = any(doc_of(c) in case["docs"] for c in r["cited"])
    facts = all(fact_found(f, r["answer"]) for f in case["must"]) and r["found"] if case["must"] else None
    return {"source": source, "facts": facts, "abstain": None, "false_abstain": not r["found"],
            "pass": r["found"] and source and facts is not False}


def rate(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def aggregate(rows: list[dict]) -> dict:
    by_type = defaultdict(list)
    for row in rows:
        by_type[row["type"]].append(row)
    costs = [row["cost_usd"] for row in rows]
    latency = sorted(row["latency_s"] for row in rows)
    return {"n": len(rows),
            **{m: rate([row["scores"][m] for row in rows]) for m in METRICS},
            "by_type": {t: {"n": len(rs), "pass": rate([r["scores"]["pass"] for r in rs])} for t, rs in sorted(by_type.items())},
            "failed": [row["id"] for row in rows if not row["scores"]["pass"]],
            "cost_per_1000_usd": round(1000 * sum(costs) / len(costs), 3),
            "latency_p50_s": latency[len(latency) // 2]}


def run(cases: list[dict]) -> list[dict]:
    from rag.answer import RAG      # loads models and the index (~1 min); --rescore does not need it
    rag = RAG()
    results = []
    for case in cases:
        r = rag.ask(case["question"])
        results.append({"id": case["id"], **r})
        print(f"{case['id']} found={r['found']!s:5} cited={len(r['cited'])} {r['latency_s']}s", flush=True)
    return results


def report(rows: list[dict], metrics: dict, prompt: str) -> str:
    def pct(v):
        return "—" if v is None else f"{v:.2f}"
    lines = [f"# Answers ({prompt}): {metrics['n']} questions\n",
             "| pass | source | facts | abstain | false abstain | cost / 1000 q | p50, s |", "|---|---|---|---|---|---|---|",
             f"| {pct(metrics['pass'])} | {pct(metrics['source'])} | {pct(metrics['facts'])} | {pct(metrics['abstain'])} "
             f"| {pct(metrics['false_abstain'])} | ${metrics['cost_per_1000_usd']} | {metrics['latency_p50_s']} |",
             "\n## By type\n", "| type | n | pass |", "|---|---|---|"]
    lines += [f"| {t} | {v['n']} | {pct(v['pass'])} |" for t, v in metrics["by_type"].items()]
    lines += ["\n## Every answer\n", "| id | type | pass | source | facts | answer |", "|---|---|---|---|---|---|"]
    mark = {True: "✓", False: "✗", None: "—"}
    for row in rows:
        s = row["scores"]
        lines.append(f"| {row['id']} | {row['type']} | {mark[s['pass']]} | {mark[s['source']]} | {mark[s['facts']]} "
                     f"| {row['answer'].replace('|', '/').replace(chr(10), ' ')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rescore", action="store_true", help="score evals/results/answers.jsonl, no model calls")
    args = parser.parse_args()
    cases = load_testset()
    if args.rescore:
        results = [json.loads(line) for line in ANSWERS.read_text(encoding="utf-8").splitlines()]
    else:
        results = run(cases)
        OUT.mkdir(parents=True, exist_ok=True)
        ANSWERS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    by_id = {r["id"]: r for r in results}
    rows = [{**by_id[c["id"]], "type": c["type"], "scores": score(by_id[c["id"]], c)} for c in cases]
    metrics = aggregate(rows)
    (OUT / "answers.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "answers.md").write_text(report(rows, metrics, results[0]["prompt"]), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "by_type"}, ensure_ascii=False))
    print(f"-> {(OUT / 'answers.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
