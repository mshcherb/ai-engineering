"""Run every text in the dataset through one model config and save the results.

Usage: python main.py [--run NAME] [--prompt VERSION] [--limit N]

Status of each text:
  ok        valid card on the first try
  repaired  first answer failed validation, the model fixed it after seeing the errors
  failed    still invalid after the one repair attempt
  error     no answer at all (network, timeout, deadline)
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

REPAIR_REQUEST = ("Your answer does not pass validation:\n{error}\n"
                  "Return the corrected card for the same text as JSON. Change only what is needed.")


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
        # field path + message for every error: the model needs them to fix its answer
        lines = [f"- {'.'.join(map(str, err['loc'])) or 'root'}: {err['msg']}" for err in e.errors()[:10]]
        return None, f"{e.error_count()} validation errors:\n" + "\n".join(lines)


def extract_with_repair(client: LLMClient, system_prompt: str, text: str,
                        temperature: float, top_p: float) -> tuple[str, dict | None, dict]:
    """Call the model, validate, and on failure give it one chance to fix the answer.

    Returns (status, card, info); info holds summed latency / tokens / cost of both calls.
    """
    first = client.extract(system_prompt, text, temperature, top_p)
    calls = [first]
    status, card, error, first_error, raw = "error", None, first.error, None, first.content
    if not first.error:
        card, error = validate(first.content)
        status = "ok"
        if card is None:
            first_error = error
            history = [{"role": "assistant", "content": first.content or ""},
                       {"role": "user", "content": REPAIR_REQUEST.format(error=error)}]
            second = client.extract(system_prompt, text, temperature, top_p, history)
            calls.append(second)
            raw = second.content
            card, error = (None, second.error) if second.error else validate(second.content)
            status = "repaired" if card else "failed"

    def total(field: str):
        values = [getattr(c, field) for c in calls if getattr(c, field) is not None]
        return round(sum(values), 6) if values else None

    info = {
        "latency_s": round(sum(c.latency_s for c in calls), 3),
        "attempts": sum(c.attempts for c in calls),
        "tokens_in": total("tokens_in"),
        "tokens_out": total("tokens_out"),
        "cost_usd": total("cost_usd"),
        "error": error if card is None else None,
        "repair_reason": first_error,     # validation error that triggered the repair
        "raw": None if card else raw,     # last invalid answer, for error analysis
    }
    return status, card, info


def main() -> None:
    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=cfg["default_run"], help="run name from config.yaml")
    parser.add_argument("--prompt", default=cfg["prompt_version"], help="prompt version from prompts/")
    parser.add_argument("--limit", type=int, help="process only the first N texts")
    args = parser.parse_args()

    run_cfg = cfg["runs"][args.run]
    provider = run_cfg["provider"]
    client = LLMClient(provider, cfg["providers"][provider], run_cfg["model"],
                       cfg["timeout_s"], cfg["max_retries"], cfg["backoff_base_s"],
                       cfg.get("max_tokens"), cfg.get("deadline_s", 120))
    prompt_version = args.prompt
    system_prompt = load_prompt(prompt_version)
    texts = load_texts(ROOT / cfg["data_path"])[: args.limit]

    out_dir = ROOT / cfg["results_dir"]
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{stamp}_{args.run}_{prompt_version}.jsonl"

    counts = {"ok": 0, "repaired": 0, "failed": 0, "error": 0}
    with out_path.open("w", encoding="utf-8") as f:
        for i, item in enumerate(texts, 1):
            status, card, info = extract_with_repair(client, system_prompt, item["text"],
                                                     run_cfg["temperature"], run_cfg["top_p"])
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
                **{k: info[k] for k in ("latency_s", "attempts", "tokens_in", "tokens_out", "cost_usd")},
                "output": card,
                "error": info["error"],
                "repair_reason": info["repair_reason"],
                "raw": info["raw"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            n_mentions = len(card["mentions"]) if card else "-"
            print(f"[{i}/{len(texts)}] {item['id']} {status:8s} {info['latency_s']:5.1f}s mentions={n_mentions}")

    print(f"\n{counts} -> {out_path.relative_to(ROOT)}")
