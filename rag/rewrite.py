"""Query rewriting: a Russian question -> an English search query + metadata filters.

    rw = Rewriter()
    r = rw.rewrite("Какая была выручка у ЖПморган чейс во втором квартале 2026 года?")
    r.query_en   # "What was JPMorgan Chase's revenue in the second quarter of 2026?"
    r.filters    # {"ticker": ["JPM"], "period_from": "2026-06-30", "period_to": "2026-09-13"}

The corpus is English, and so are the embedding model (bge-small-en) and BM25, so a Russian
question as is finds little. gpt-4o-mini translates it and pulls out companies and the period;
the code, not the model, turns the period into a date range.

Answers are cached in evals/rewrite_cache.jsonl by (prompt version, model, question): a rerun costs
nothing and gives the same queries, and the cache shows exactly what the model returned.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from extractor.client import LLMClient
from extractor.run import load_prompt
from extractor.schema import json_schema
from rag.index import load_chunks

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "evals" / "rewrite_cache.jsonl"
QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
# A chunk's period is the end of the reported period (annual reports, TSMC) or the release date
# (US earnings releases, 2-6 weeks after the quarter); 75 days covers both, and stops before the
# next quarter's release, so the Q2 release does not pass a Q3 filter.
REPORT_LAG_DAYS = 75


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int
    quarter: int | None = Field(description="1-4, null for a full year")
    fiscal: bool = Field(description="True only if the question says fiscal year")


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_en: str = Field(description="The question as a clear English sentence")
    tickers: list[str] = Field(description="Upper-case tickers of the companies asked about")
    period: Period | None = Field(description="Reporting period asked about, null if none or a forecast")


@dataclass
class Rewrite:
    question: str
    query_en: str
    tickers: list[str] = field(default_factory=list)
    period: dict | None = None
    error: str | None = None
    cost_usd: float | None = None
    latency_s: float = 0.0

    @property
    def filters(self) -> dict | None:
        filters = {}
        if self.tickers:
            filters["ticker"] = self.tickers
        if span := period_range(self.period):
            filters["period_from"], filters["period_to"] = span
        return filters or None


def period_range(period: dict | None) -> tuple[str, str] | None:
    """Q3 2026 -> 2026-09-30 .. 2026-12-14; 2025 -> 2025-12-31 .. 2026-03-16.
    Fiscal periods get no date filter: NVIDIA's fiscal Q2 2027 ends in July 2026, Micron's fiscal
    year in early September, and the corpus does not store each company's fiscal calendar."""
    if not period or period["fiscal"] or not 1 <= (period["quarter"] or 4) <= 4:
        return None
    end = date.fromisoformat(f"{period['year']}-{QUARTER_END[period['quarter'] or 4]}")
    return end.isoformat(), (end + timedelta(days=REPORT_LAG_DAYS)).isoformat()


def corpus_companies() -> str:
    """'- JPM: JPMORGAN CHASE & CO' lines, from the chunks, so the prompt follows the corpus."""
    names: dict[str, str] = {}
    for c in load_chunks("sections"):
        if len(c["company"]) > len(names.get(c["ticker"], "")):   # TSMC PDFs carry just "TSM"
            names[c["ticker"]] = c["company"]
    return "\n".join(f"- {t}: {n}" for t, n in sorted(names.items()))


class Rewriter:
    def __init__(self, prompt_version: str | None = None, run: str | None = None, cache: Path = CACHE):
        load_dotenv(ROOT / ".env")
        cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.prompt_version = prompt_version or cfg["rewrite"]["prompt_version"]
        self.run_cfg = cfg["runs"][run or cfg["rewrite"]["run"]]
        self.cfg = cfg
        self.system_prompt = load_prompt(self.prompt_version).replace("{companies}", corpus_companies())
        self.cache_path = cache
        self.cache = {}
        if cache.exists():
            for line in cache.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.cache[rec["key"]] = rec
        self._client: LLMClient | None = None

    def key(self, question: str) -> str:
        raw = f"{self.prompt_version}|{self.run_cfg['model']}|{question.strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def client(self) -> LLMClient:
        # created on the first cache miss: a fully cached run needs no API key
        if self._client is None:
            provider = self.run_cfg["provider"]
            self._client = LLMClient(provider, self.cfg["providers"][provider], self.run_cfg["model"],
                                     self.cfg["timeout_s"], self.cfg["max_retries"], self.cfg["backoff_base_s"],
                                     self.cfg.get("max_tokens"), self.cfg.get("deadline_s", 120))
        return self._client

    def rewrite(self, question: str) -> Rewrite:
        key = self.key(question)
        if key in self.cache:
            rec = self.cache[key]
            return Rewrite(question, rec["query_en"], rec["tickers"], rec["period"], None,
                           rec.get("cost_usd"), rec.get("latency_s", 0.0))
        call = self.client.extract(self.system_prompt, question, self.run_cfg["temperature"],
                                   self.run_cfg["top_p"], schema=json_schema(SearchRequest))
        try:
            if call.error:
                raise ValueError(call.error)
            req = SearchRequest.model_validate_json(call.content or "")
        except (ValueError, ValidationError) as e:
            # no rewrite is better than no answer: search with the question as is, without filters
            return Rewrite(question, question, error=f"{type(e).__name__}: {e}"[:300],
                           cost_usd=call.cost_usd, latency_s=call.latency_s)
        out = Rewrite(question, req.query_en, sorted({t.strip().upper() for t in req.tickers}),
                      req.period.model_dump() if req.period else None, None, call.cost_usd, call.latency_s)
        rec = {"key": key, "prompt": self.prompt_version, "model": self.run_cfg["model"], "question": question,
               "query_en": out.query_en, "tickers": out.tickers, "period": out.period,
               "cost_usd": out.cost_usd, "latency_s": out.latency_s}
        self.cache[key] = rec
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return out


if __name__ == "__main__":
    import sys
    r = Rewriter().rewrite(" ".join(sys.argv[1:]) or "Какая грос маргин TSMC в третьем квартале 2026 года?")
    print(json.dumps({"query_en": r.query_en, "tickers": r.tickers, "period": r.period,
                      "filters": r.filters, "error": r.error, "cost_usd": r.cost_usd}, ensure_ascii=False, indent=2))
