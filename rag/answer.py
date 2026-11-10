"""RAG answer with sources: rewrite -> search -> context within a token budget -> grounded answer.

    python -m rag.answer "Какую выручку показал JPMorgan в третьем квартале 2026 года?"
    python -m rag.answer --sample        # the retrieval questions -> evals/results/answers_sample_<prompt>.md

    rag = RAG()
    r = rag.ask("Какая грос маргин TSMC в третьем квартале 2026 года?")
    r["found"], r["answer"], r["cited"]      # cited = chunk ids the answer relies on
    r["context"]                             # {chunk_id: text} the model saw, for faithfulness checks

Based on the lesson 9 rag.py: source labels [S1].., a token budget for the context, structured
output {found, answer, citations} and citation checks in code. Differences: the question goes
through the query rewriting layer, the answer is in Russian with a label after every claim, and a
period filter that leaves nothing is dropped once (a forecast for Q4 sits in the Q3 report).
"""
import argparse
import json
import re
import time
from pathlib import Path

import tiktoken
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from extractor.run import load_prompt
from extractor.schema import json_schema
from rag.rewrite import Rewriter, load_config, make_client
from rag.search import Retriever

ROOT = Path(__file__).resolve().parent.parent
MODE = "hybrid+rerank"
NOT_FOUND = "В документах этого нет."
ENC = tiktoken.get_encoding("o200k_base")   # the tokenizer of gpt-4o / gpt-4o-mini
LABEL_RE = re.compile(r"\[\s*(S\d+)\s*\]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = Field(description="False when the sources do not contain the answer")
    answer: str = Field(description="The answer in Russian with [Sn] after every claim, or what is missing")
    citations: list[str] = Field(description='Labels used in the answer, e.g. ["S1", "S3"]')


def count_tokens(text: str) -> int:
    return len(ENC.encode(text))


def source_name(chunk: dict) -> str:
    """'JPM 8-K EX-99.1 quarterly earnings release, period 2026-10-13 · Section: ... · p. 3'."""
    parts = [chunk["title"]]
    if chunk["section"]:
        parts.append(f"Section: {chunk['section']}")
    if chunk.get("page"):
        parts.append(f"p. {chunk['page']}")
    return " · ".join(parts)


def build_context(hits: list[dict], budget: int) -> tuple[str, dict]:
    """Context text and {label: chunk} for the chunks that fit into `budget` tokens, best first.
    A chunk that does not fit is skipped, a shorter one further down may still fit."""
    parts, sources, used = [], {}, 0
    for hit in hits:
        label = f"S{len(sources) + 1}"
        block = f"[{label}] {source_name(hit)}\n{hit['text']}"
        size = count_tokens(block)
        if used + size > budget:
            continue
        parts.append(block)
        sources[label] = hit
        used += size
    return "\n\n".join(parts), sources


def check_citations(ans: Answer, sources: dict) -> dict:
    """Labels in the text are what the reader sees, so they are what counts; the `citations`
    field is only cross-checked. Labels of sources the model never got are removed."""
    inline = [m.group(1) for m in LABEL_RE.finditer(ans.answer)]
    invalid = sorted({c for c in inline + [c.strip("[] ") for c in ans.citations] if c not in sources})
    text = LABEL_RE.sub(lambda m: m.group(0) if m.group(1) in sources else "", ans.answer).strip()
    cited = list(dict.fromkeys(c for c in inline if c in sources))
    # a sentence with a number but no label is a claim without a source; a "not found" note has no claims
    uncited = [s for s in SENTENCE_RE.split(text) if re.search(r"\d", s) and not LABEL_RE.search(s)] if cited else []
    return {"found": ans.found and bool(cited), "text": text, "cited": cited, "invalid": invalid,
            "uncited_claims": uncited}


class RAG:
    def __init__(self, chunk_set: str = "sections", prompt_version: str | None = None):
        cfg = load_config()
        self.settings = cfg["answer"]
        self.prompt_version = prompt_version or self.settings["prompt_version"]
        self.run_cfg = cfg["runs"][self.settings["run"]]
        self.system_prompt = load_prompt(self.prompt_version)
        self.client = make_client(cfg, self.run_cfg)
        self.rewriter = Rewriter()
        self.retriever = Retriever(chunk_set)

    def retrieve(self, query: str, filters: dict | None) -> tuple[list[dict], dict | None, bool]:
        """Returns (hits, filters actually used, whether the period filter was dropped)."""
        k = self.settings["k"]
        hits = self.retriever.search(query, MODE, filters, k=k)
        if not hits and filters and "period_from" in filters:
            loose = {key: v for key, v in filters.items() if key not in ("period_from", "period_to")} or None
            return self.retriever.search(query, MODE, loose, k=k), loose, True
        return hits, filters, False

    def ask(self, question: str) -> dict:
        start = time.perf_counter()
        rw = self.rewriter.rewrite(question)
        hits, filters, dropped = self.retrieve(rw.query_en, rw.filters)
        result = {"question": question, "query_en": rw.query_en, "filters": filters, "period_dropped": dropped,
                  "retrieved": [h["chunk_id"] for h in hits], "found": False, "answer": NOT_FOUND,
                  "cited": [], "sources": [], "invalid": [], "uncited_claims": [], "context": {},
                  "context_tokens": 0, "prompt": self.prompt_version, "error": rw.error,
                  "cost_usd": rw.cost_usd or 0.0}
        if hits:
            context, sources = build_context(hits, self.settings["context_budget"])
            # the original question, not query_en: the user's own words (e.g. a product name) win
            call = self.client.extract(self.system_prompt, f"<sources>\n{context}\n</sources>\n\nQuestion: {question}",
                                       self.run_cfg["temperature"], self.run_cfg["top_p"], schema=json_schema(Answer))
            result.update(context={s["chunk_id"]: s["text"] for s in sources.values()},
                          context_tokens=count_tokens(context), cost_usd=result["cost_usd"] + (call.cost_usd or 0.0))
            try:
                if call.error:
                    raise ValueError(call.error)
                checked = check_citations(Answer.model_validate_json(call.content or ""), sources)
            except (ValueError, ValidationError) as e:
                result["error"] = f"{type(e).__name__}: {e}"[:300]
                checked = None
            if checked:
                result.update(invalid=checked["invalid"], uncited_claims=checked["uncited_claims"])
                if checked["found"]:
                    result.update(found=True, answer=checked["text"],
                                  cited=[sources[c]["chunk_id"] for c in checked["cited"]],
                                  sources=[{"label": c, "chunk_id": sources[c]["chunk_id"], "name": source_name(sources[c]),
                                            "url": sources[c]["url"]} for c in checked["cited"]])
                else:
                    result["missing"] = checked["text"]   # the model's note on what is missing
        result["latency_s"] = round(time.perf_counter() - start, 2)
        return result


def render(r: dict) -> str:
    lines = [r["answer"]]
    if r["sources"]:
        lines += ["", "Источники:"] + [f"[{s['label']}] {s['name']}\n      {s['url']}" for s in r["sources"]]
    elif r.get("missing"):
        lines += ["", f"({r['missing']})"]
    return "\n".join(lines)


def sample(rag: RAG) -> None:
    """Every retrieval question through the pipeline, as a markdown file to read by hand."""
    from evals.retrieval_eval import QUESTIONS, load_questions
    out = ROOT / "evals" / "results" / f"answers_sample_{rag.prompt_version}.md"
    lines = [f"# Answers ({rag.prompt_version}): retrieval questions\n"]
    cost, questions = 0.0, load_questions(QUESTIONS)
    for q in questions:
        r = rag.ask(q["question"])
        cost += r["cost_usd"]
        flags = [f for f, on in (("period filter dropped", r["period_dropped"]), (f"invalid labels {r['invalid']}", r["invalid"]),
                                 (f"{len(r['uncited_claims'])} uncited claims", r["uncited_claims"]),
                                 (f"error: {r['error']}", r["error"])) if on]
        expected = q["evidence"][0] if q["evidence"] else "нет ответа в корпусе"
        lines += [f"## {q['id']} ({q['type']}): {q['question']}", "",
                  f"Ожидается: {expected} — {', '.join(q['docs']) or '—'}", "",
                  render(r).replace("\n      ", "\n  "), "",
                  f"`found={r['found']}` · {r['context_tokens']} context tokens · {r['latency_s']} s"
                  + (f" · {'; '.join(flags)}" if flags else ""), ""]
        print(f"{q['id']} found={r['found']!s:5} cited={len(r['cited'])} {'; '.join(flags)}", flush=True)
    lines.insert(1, f"{len(questions)} questions, cost ${cost:.4f} (rewrite + answer)\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {out.relative_to(ROOT)}  (cost ${cost:.4f})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="*")
    parser.add_argument("--sample", action="store_true", help="run the retrieval questions, write a markdown file")
    parser.add_argument("--json", action="store_true", help="print the full result")
    args = parser.parse_args()
    rag = RAG()
    if args.sample:
        sample(rag)
    else:
        r = rag.ask(" ".join(args.question) or "Какая грос маргин TSMC в третьем квартале 2026 года?")
        print(json.dumps({k: v for k, v in r.items() if k != "context"}, ensure_ascii=False, indent=2)
              if args.json else render(r))
