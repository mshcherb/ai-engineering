"""LLM as a judge: correctness against the reference and faithfulness to the cited sources,
plus its calibration on answers a person labelled by hand (evals/labels.jsonl).

    python -m evals.judge --calibrate                  # judge vs person on the labelled answers
    python -m evals.judge --calibrate --correct-prompt judge_correct_v2

    judge = Judge()
    judge.correct(case, answer)        -> (True / False, reason)
    judge.grounded(answer, sources)    -> (True / False, [unsupported claims])

The judge is a model too: before its numbers count, it has to agree with a person.
"""
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evals.retrieval_eval import load_questions
from evals.testset import load_testset
from extractor.run import load_prompt
from extractor.schema import json_schema
from rag.answer import source_name
from rag.rewrite import load_config, make_client

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "evals" / "labels.jsonl"
OUT = ROOT / "evals" / "results"


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(description="One or two sentences naming the key fact compared")
    verdict: Literal["correct", "incorrect"]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    supported: bool


class Claims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[Claim]


class Judge:
    def __init__(self, correct_prompt: str | None = None, grounded_prompt: str | None = None, run: str | None = None):
        cfg = load_config()
        settings = cfg["judge"]
        self.run_cfg = cfg["runs"][run or settings["run"]]
        self.correct_version = correct_prompt or settings["correct_prompt"]
        self.grounded_version = grounded_prompt or settings["grounded_prompt"]
        self.correct_prompt = load_prompt(self.correct_version)
        self.grounded_prompt = load_prompt(self.grounded_version)
        self.client = make_client(cfg, self.run_cfg)
        self.cost_usd = 0.0

    def _ask(self, system: str, user: str, model: type[BaseModel]) -> BaseModel:
        call = self.client.extract(system, user, self.run_cfg["temperature"], self.run_cfg["top_p"], schema=json_schema(model))
        self.cost_usd += call.cost_usd or 0.0
        if call.error:
            raise RuntimeError(f"judge call failed: {call.error}")
        return model.model_validate_json(call.content or "")

    def correct(self, case: dict, answer: str) -> tuple[bool, str]:
        user = (f"<question>{case['question']}</question>\n<reference>{case['reference']}</reference>\n"
                f"<answer>{answer}</answer>")
        v = self._ask(self.correct_prompt, user, Verdict)
        return v.verdict == "correct", v.reason

    def grounded(self, answer: str, sources: list[str]) -> tuple[bool, list[str]]:
        """Call only for answers that were given ("не знаю" has no claims)."""
        text = "\n\n".join(f"<source>\n{s}\n</source>" for s in sources)
        claims = self._ask(self.grounded_prompt, f"<sources>\n{text}\n</sources>\n\n<answer>{answer}</answer>", Claims).claims
        unsupported = [c.claim for c in claims if not c.supported]
        return not unsupported, unsupported


def agreement(judged: list[bool], human: list[bool], ids: list[str]) -> dict:
    n = len(human)
    return {"n": n,
            "agreement": round(sum(j == h for j, h in zip(judged, human)) / n, 3),
            # the dangerous direction: the judge passes what a person failed
            "false_pass": round(sum(j and not h for j, h in zip(judged, human)) / n, 3),
            "false_fail": round(sum(h and not j for j, h in zip(judged, human)) / n, 3),
            "disagreements": [i for i, j, h in zip(ids, judged, human) if j != h]}


def chunk_texts() -> dict[str, str]:
    """chunk id -> the source as the bot saw it: document, period and section first, then the text.
    Without the header "во втором квартале 2026" cannot be checked: the quarter is often only in the title."""
    with open(ROOT / "data" / "corpus" / "chunks.jsonl", encoding="utf-8") as f:
        return {c["chunk_id"]: f"{source_name(c)}\n{c['text']}" for c in map(json.loads, f)}


def calibrate(judge: Judge) -> None:
    cases = {c["id"]: c for c in load_testset()}
    texts = chunk_texts()
    items = load_questions(LABELS)
    rows = []
    for it in items:
        row = {"id": it["id"], "human_correct": it["correct"], "human_grounded": it["grounded"]}
        if it["correct"] is not None:
            row["judge_correct"], row["correct_reason"] = judge.correct(cases[it["case"]], it["answer"])
        if it["grounded"] is not None and it["found"]:
            row["judge_grounded"], row["unsupported"] = judge.grounded(it["answer"], [texts[c] for c in it["cited"]])
        rows.append(row)
        print(f"{it['id']} correct {row['human_correct']}/{row.get('judge_correct')} "
              f"grounded {row['human_grounded']}/{row.get('judge_grounded')}", flush=True)
    result = {}
    for metric in ("correct", "grounded"):
        rs = [r for r in rows if f"judge_{metric}" in r]
        if rs:
            result[metric] = agreement([r[f"judge_{metric}"] for r in rs], [r[f"human_{metric}"] for r in rs], [r["id"] for r in rs])
    name = f"calibration_{judge.correct_version}_{judge.grounded_version}_{judge.run_cfg['model'].split('/')[-1]}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps({"summary": result, "rows": rows, "cost_usd": round(judge.cost_usd, 4)},
                                                 indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Judge calibration: {judge.correct_version} + {judge.grounded_version} ({judge.run_cfg['model']})\n",
             "| judge | n | agreement | false pass | false fail | disagreements |", "|---|---|---|---|---|---|"]
    for metric, r in result.items():
        lines.append(f"| {metric} | {r['n']} | {r['agreement']:.2f} | {r['false_pass']:.2f} | {r['false_fail']:.2f} "
                     f"| {', '.join(r['disagreements']) or '—'} |")
    lines += ["\n## Disagreements\n"]
    for r in rows:
        if r.get("judge_correct") is not None and r["judge_correct"] != r["human_correct"]:
            lines.append(f"- **{r['id']} correct**: person {r['human_correct']}, judge {r['judge_correct']}: {r['correct_reason']}")
        if r.get("judge_grounded") is not None and r["judge_grounded"] != r["human_grounded"]:
            lines.append(f"- **{r['id']} grounded**: person {r['human_grounded']}, judge {r['judge_grounded']}; "
                         f"unsupported: {r['unsupported']}")
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), f"cost ${judge.cost_usd:.4f}")
    print(f"-> {(OUT / f'{name}.md').relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--correct-prompt")
    parser.add_argument("--grounded-prompt")
    parser.add_argument("--run", help="a run from config.yaml to judge with")
    args = parser.parse_args()
    if args.calibrate:
        calibrate(Judge(args.correct_prompt, args.grounded_prompt, args.run))
