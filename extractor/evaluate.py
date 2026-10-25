"""Compare result files against the golden set and print a metrics table.

Usage: python -m extractor.evaluate [RESULT_FILE ...]
Without arguments takes the latest result file of every run/prompt version in results/.
Writes results/metrics.md (comparison table) and results/errors.md (every mismatch).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent

FIELDS = ("sentiment", "asset_type", "horizon", "price_target")
NAME_SUFFIXES = {"inc", "corp", "corporation", "co", "company", "ltd", "plc", "llc",
                 "group", "holdings", "the", "sa", "se", "ag", "nv", "class", "a", "b"}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def latest_results(results_dir: Path) -> list[Path]:
    """Latest file per run+prompt version; file names are <stamp>_<run>_<version>.jsonl."""
    latest = {}
    for p in sorted(results_dir.glob("*.jsonl")):
        key = p.stem.split("_", 1)[1]
        latest[key] = p  # sorted by timestamp, so the last one wins
    return list(latest.values())


def norm_ticker(t: str | None) -> str | None:
    """'$mc.pa' -> 'MC'; models sometimes write the string "null" instead of null."""
    if not t or t.strip().lower() in {"null", "none", "n/a"}:
        return None
    return t.strip().lstrip("$").split(".")[0].upper() or None


def norm_name(name: str) -> str:
    words = re.sub(r"[^\w\s]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in NAME_SUFFIXES)


def same_security(g: dict, p: dict) -> bool:
    """Match by ticker when both have one, otherwise by company name.

    A name equal to the other side's ticker also counts ("BOXX" vs ticker BOXX).
    """
    gt, pt = norm_ticker(g["ticker"]), norm_ticker(p["ticker"])
    if gt and pt:
        return gt == pt
    gn, pn = norm_name(g["company"]), norm_name(p["company"])
    if (gt and pn.upper() == gt) or (pt and gn.upper() == pt):
        return True
    if not gn or not pn:
        return False
    return gn == pn or (min(len(gn), len(pn)) >= 3 and (gn in pn or pn in gn))


def match_mentions(gold: list[dict], pred: list[dict]) -> list[tuple[dict, dict]]:
    """Greedy one-to-one matching of gold mentions to predicted ones."""
    pairs, used = [], set()
    for g in gold:
        for j, p in enumerate(pred):
            if j not in used and same_security(g, p):
                pairs.append((g, p))
                used.add(j)
                break
    return pairs


def field_equal(field: str, g, p) -> bool:
    if field == "price_target" and g is not None and p is not None:
        return abs(g - p) <= 0.01 * abs(g)
    return g == p


def pct(num: int, den: int) -> float | None:
    return 100 * num / den if den else None


def evaluate(records: list[dict], golden: dict[str, dict]) -> tuple[dict, list[str]]:
    by_id = {r["id"]: r for r in records}
    n = len(records)
    ok = sum(r["status"] == "ok" for r in records)
    latencies = [r["latency_s"] for r in records]
    costs = [r["cost_usd"] or 0.0 for r in records]  # local model: no API cost

    hits = defaultdict(int)       # field -> correct count
    totals = defaultdict(int)     # field -> compared count
    tp = fp = fn = 0
    errors = []
    for gid, gold in golden.items():
        rec = by_id.get(gid)
        card = rec["output"] if rec else None
        if card is None:
            # invalid / missing answer: every field counts as wrong
            for f in ("is_about_stocks", "language"):
                totals[f] += 1
            fn += len(gold["mentions"])
            errors.append(f"- **{gid}**: no valid output ({rec['status'] if rec else 'missing'})")
            continue
        for f in ("is_about_stocks", "language"):
            totals[f] += 1
            if card[f] == gold[f]:
                hits[f] += 1
            else:
                errors.append(f"- **{gid}** `{f}`: gold `{gold[f]}` / pred `{card[f]}`")

        pairs = match_mentions(gold["mentions"], card["mentions"])
        tp += len(pairs)
        fp += len(card["mentions"]) - len(pairs)
        fn += len(gold["mentions"]) - len(pairs)
        matched_g = {id(g) for g, _ in pairs}
        matched_p = {id(p) for _, p in pairs}
        for g in gold["mentions"]:
            if id(g) not in matched_g:
                errors.append(f"- **{gid}** missed: {g['company']} ({g['ticker']})")
        for p in card["mentions"]:
            if id(p) not in matched_p:
                errors.append(f"- **{gid}** extra: {p['company']} ({p['ticker']})")
        for g, p in pairs:
            for f in FIELDS:
                totals[f] += 1
                if field_equal(f, g[f], p[f]):
                    hits[f] += 1
                else:
                    errors.append(f"- **{gid}** {g['company']} `{f}`: gold `{g[f]}` / pred `{p[f]}`")

    precision, recall = pct(tp, tp + fp), pct(tp, tp + fn)
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    first = records[0]
    metrics = {
        "run": first["run"],
        "model": first["model"],
        "prompt": first["prompt_version"],
        "temp/top_p": f"{first['temperature']}/{first['top_p']}",
        "n": n,
        "valid_%": pct(ok, n),
        "p50_s": float(np.percentile(latencies, 50)),
        "p95_s": float(np.percentile(latencies, 95)),
        "usd_per_1000": 1000 * sum(costs) / n,
        "about_stocks_%": pct(hits["is_about_stocks"], totals["is_about_stocks"]),
        "language_%": pct(hits["language"], totals["language"]),
        "mention_P_%": precision,
        "mention_R_%": recall,
        "mention_F1_%": f1,
        **{f"{f}_%": pct(hits[f], totals[f]) for f in FIELDS},
    }
    return metrics, errors


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.1f}" if abs(v) >= 0.1 or v == 0 else f"{v:.4f}"
    return str(v)


def to_markdown(rows: list[dict]) -> str:
    """Runs as columns, metrics as rows: easier to read with many metrics."""
    keys = [k for k in rows[0] if k != "run"]
    lines = ["| metric | " + " | ".join(r["run"] for r in rows) + " |",
             "|---|" + "---|" * len(rows)]
    lines += [f"| {k} | " + " | ".join(fmt(r[k]) for r in rows) + " |" for k in keys]
    return "\n".join(lines)


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    results_dir = ROOT / cfg["results_dir"]
    golden = {g["id"]: g["label"]
              for g in json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))}

    paths = [Path(a) for a in sys.argv[1:]] or latest_results(results_dir)
    rows, details = [], []
    for path in sorted(paths):
        metrics, errors = evaluate(load_jsonl(path), golden)
        rows.append(metrics)
        details.append(f"## {metrics['run']} ({metrics['prompt']}) — `{path.name}`\n\n"
                       + ("\n".join(errors) or "no mismatches") + "\n")

    table = to_markdown(rows)
    header = (f"Golden set: {len(golden)} texts. valid / latency / cost — over all texts of a run; "
              "field accuracy — on matched mentions only; cost per 1000 docs, local model = $0 API.\n\n")
    (results_dir / "metrics.md").write_text("# Metrics\n\n" + header + table + "\n", encoding="utf-8")
    (results_dir / "errors.md").write_text("# Mismatches vs golden set\n\n" + "\n".join(details),
                                           encoding="utf-8")
    print(table)
    print(f"\n-> {cfg['results_dir']}/metrics.md, {cfg['results_dir']}/errors.md")


if __name__ == "__main__":
    main()
