"""The answer testset (evals/testset.jsonl) and its lint: test the tests before trusting their numbers.

    python -m evals.testset          # prints problems, exit code 1 if there are any

A typo in a doc id or a `must` fact the document never says makes a case fail forever, and the
bot gets "fixed" for a bug that lives in the testset.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from evals.retrieval_eval import load_questions, norm
from evals.scoring import fact_found, value_of

ROOT = Path(__file__).resolve().parent.parent
TESTSET = ROOT / "evals" / "testset.jsonl"
TYPES = {"fact", "version_trap", "similar_docs", "narrative", "no_answer"}
TYPE_MIN = 2         # a type with one case says nothing


def load_testset(path: Path = TESTSET) -> list[dict]:
    return load_questions(path)


def lint(cases: list[dict], chunks_by_doc: dict[str, list[str]]) -> list[str]:
    problems = []
    for cid, n in Counter(c["id"] for c in cases).items():
        if n > 1:
            problems.append(f"{cid}: duplicate id")
    for t, n in Counter(c["type"] for c in cases).items():
        if n < TYPE_MIN:
            problems.append(f"type {t}: only {n} case(s), need {TYPE_MIN}")
    for c in cases:
        cid = c["id"]
        if c["type"] not in TYPES:
            problems.append(f"{cid}: unknown type {c['type']}")
        if not c.get("reference"):
            problems.append(f"{cid}: no reference answer")
        if c["type"] == "no_answer":
            if c["docs"] or c["must"] or c["evidence"]:
                problems.append(f"{cid}: no_answer case with docs, must or evidence")
            continue
        if not c["docs"]:
            problems.append(f"{cid}: no expected documents")
        unknown = [d for d in c["docs"] if d not in chunks_by_doc]
        if unknown:
            problems.append(f"{cid}: unknown docs {unknown}")
        texts = [t for d in c["docs"] for t in chunks_by_doc.get(d, [])]
        for e in c["evidence"]:
            if not any(norm(e) in norm(t) for t in texts):
                problems.append(f"{cid}: evidence not in the expected docs: {e!r}")
        for f in c["must"]:
            try:
                value_of(f)
            except ValueError as e:
                problems.append(f"{cid}: {e}")
                continue
            if not any(fact_found(f, t) for t in texts):
                problems.append(f"{cid}: must fact not in the expected docs: {f!r}")
    return problems


def chunks_by_doc() -> dict[str, list[str]]:
    docs = {row["doc_id"]: [] for row in csv.DictReader(open(ROOT / "data" / "corpus" / "manifest.csv", encoding="utf-8"))}
    with open(ROOT / "data" / "corpus" / "chunks.jsonl", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            docs.setdefault(c["doc_id"], []).append(c["text"])
    return docs


def main() -> None:
    cases = load_testset()
    problems = lint(cases, chunks_by_doc())
    types = Counter(c["type"] for c in cases)
    reviewed = sum(bool(c.get("reviewed")) for c in cases)
    print(f"{len(cases)} cases, reviewed {reviewed}/{len(cases)}: " + ", ".join(f"{t} {n}" for t, n in sorted(types.items())))
    for p in problems:
        print("  -", p)
    print("lint: OK" if not problems else f"lint: {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
