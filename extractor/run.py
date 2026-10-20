"""Run every text in the dataset through one model config and save the results.

Usage: python main.py [--run NAME] [--limit N]
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from extractor.client import LLMClient
from extractor.schema import PostCard

ROOT = Path(__file__).resolve().parent.parent


def load_prompt(version: str) -> str:
    text = (ROOT / "prompts" / f"{version}.md").read_text(encoding="utf-8")
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()  # drop front matter


def load_texts(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate(content: str | None) -> tuple[dict | None, str | None]:
    """Parse model output against the schema. Returns (card, error)."""
    if content is None:
        return None, "empty response"
    try:
        return PostCard.model_validate_json(content).model_dump(mode="json"), None
    except ValidationError as e:
        return None, f"ValidationError: {e.error_count()} errors: {e.errors()[0]['msg']}"


def main() -> None:
    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=cfg["default_run"], help="run name from config.yaml")
    parser.add_argument("--limit", type=int, help="process only the first N texts")
    args = parser.parse_args()

    run_cfg = cfg["runs"][args.run]
    provider = run_cfg["provider"]
    client = LLMClient(provider, cfg["providers"][provider], run_cfg["model"],
                       cfg["timeout_s"], cfg["max_retries"], cfg["backoff_base_s"])
    prompt_version = cfg["prompt_version"]
    system_prompt = load_prompt(prompt_version)
    texts = load_texts(ROOT / cfg["data_path"])[: args.limit]

    out_dir = ROOT / cfg["results_dir"]
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{stamp}_{args.run}_{prompt_version}.jsonl"

    counts = {"ok": 0, "invalid": 0, "error": 0}
    with out_path.open("w", encoding="utf-8") as f:
        for i, item in enumerate(texts, 1):
            res = client.extract(system_prompt, item["text"],
                                 run_cfg["temperature"], run_cfg["top_p"])
            card, err = (None, res.error) if res.error else validate(res.content)
            status = "ok" if card else ("error" if res.error else "invalid")
            counts[status] += 1
            record = {
                "id": item["id"],
                "run": args.run,
                "provider": provider,
                "model": run_cfg["model"],
                "prompt_version": prompt_version,
                "temperature": run_cfg["temperature"],
                "top_p": run_cfg["top_p"],
                "status": status,
                "latency_s": res.latency_s,
                "attempts": res.attempts,
                "tokens_in": res.tokens_in,
                "tokens_out": res.tokens_out,
                "cost_usd": res.cost_usd,
                "output": card,
                "error": err,
                "raw": None if card else res.content,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            n_mentions = len(card["mentions"]) if card else "-"
            print(f"[{i}/{len(texts)}] {item['id']} {status:7s} {res.latency_s:5.1f}s mentions={n_mentions}")

    print(f"\n{counts} -> {out_path.relative_to(ROOT)}")
