"""Build data/texts.jsonl from raw Telegram exports and cleaned Reddit posts.

Raw data lives in notes/dirty data/ (not in git: contains usernames / PII).
This script picks a diverse, anonymized subset and writes it to data/.

Usage: python scripts/build_dataset.py
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "notes" / "dirty data"
OUT = ROOT / "data" / "texts.jsonl"

# Raw file -> neutral source label (channel names may contain real names)
TELEGRAM = {"more_gold.json": "telegram/ch1", "smart_investor.json": "telegram/ch2"}
REDDIT = "reddit_clean.json"

SEED = 42
# How many texts to take from each bucket
QUOTAS = {
    "tg_cashtag": 14,        # $TICKER mentions
    "tg_company_words": 4,   # company named by words, no $
    "tg_market": 6,          # about markets but no specific company
    "tg_noise": 5,           # not about stocks at all
    "rd_stocks": 15,         # r/stocks posts
    "rd_investing": 6,       # r/investing (mostly personal finance)
}
# Message ids excluded by hand: contain personal names / private links
EXCLUDE_IDS = {"telegram/ch1:10366", "telegram/ch2:1640"}

URL_RE = re.compile(r"https?://\S+|www\.\S+|t\.me/\S+")
MENTION_RE = re.compile(r"(?<!\w)@\w{3,}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
CASHTAG_RE = re.compile(r"\$[A-Z]{1,5}\b")
COMPANY_WORDS = re.compile(
    r"\b(nvidia|нвидиа|tesla|тесла|apple|эпл|google|гугл|alphabet|microsoft|"
    r"amazon|амазон|meta|asml|tsmc|micron|samsung|самсунг|intel|amd|netflix|"
    r"revolut|palantir|broadcom|oracle|robinhood|jpmorgan|goldman)\b",
    re.IGNORECASE,
)
MARKET_WORDS = re.compile(
    r"(рын|акци|фонд|индекс|s&p|nasdaq|ставк|фрс|инвест|портфел|облигац|"
    r"дивиденд|бирж|трейд|market|stock)",
    re.IGNORECASE,
)


def anonymize(text: str) -> str:
    text = URL_RE.sub("<URL>", text)
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = MENTION_RE.sub("@<USER>", text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tg_text(msg: dict) -> str:
    """Telegram stores text as a string or a list of strings / entity dicts."""
    raw = msg.get("text") or ""
    if isinstance(raw, list):
        raw = "".join(p if isinstance(p, str) else p.get("text", "") for p in raw)
    return raw


def load_telegram() -> list[dict]:
    items = []
    for fname, source in TELEGRAM.items():
        chat = json.loads((RAW / fname).read_text(encoding="utf-8"))
        for msg in chat["messages"]:
            if msg.get("type") != "message":
                continue
            text = anonymize(tg_text(msg))
            key = f"{source}:{msg['id']}"
            if len(text) < 3 or key in EXCLUDE_IDS:
                continue
            items.append({"key": key, "source": source,
                          "date": msg["date"][:10], "text": text})
    return items


def load_reddit() -> list[dict]:
    posts = json.loads((RAW / REDDIT).read_text(encoding="utf-8"))
    items = []
    for p in posts:
        text = anonymize(f"{p['title']}\n\n{p['text']}")
        items.append({"key": f"{p['source']}:{p['id']}", "source": p["source"],
                      "date": p["date"], "text": text})
    return items


def bucket(item: dict) -> str:
    text, src = item["text"], item["source"]
    if src.startswith("reddit"):
        return "rd_stocks" if src.endswith("r/stocks") else "rd_investing"
    if CASHTAG_RE.search(text):
        return "tg_cashtag"
    if COMPANY_WORDS.search(text):
        return "tg_company_words"
    if MARKET_WORDS.search(text):
        return "tg_market"
    return "tg_noise"


def pick(items: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Take n items spread across short / medium / long texts."""
    by_len = sorted(items, key=lambda x: len(x["text"]))
    thirds = [by_len[i::3] for i in range(3)] if len(by_len) > n else [by_len]
    chosen, i = [], 0
    pools = [rng.sample(t, len(t)) for t in thirds]
    while len(chosen) < min(n, len(items)):
        pool = pools[i % len(pools)]
        if pool:
            chosen.append(pool.pop())
        i += 1
    return chosen


def main() -> None:
    rng = random.Random(SEED)
    items = load_telegram() + load_reddit()
    buckets: dict[str, list[dict]] = {}
    for it in items:
        buckets.setdefault(bucket(it), []).append(it)

    selected = []
    for name, n in QUOTAS.items():
        got = pick(buckets.get(name, []), n, rng)
        print(f"{name:18s} available {len(buckets.get(name, [])):3d}  picked {len(got)}")
        selected += [{**g, "bucket": name} for g in got]

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, it in enumerate(selected, 1):
            rec = {"id": f"t{i:03d}", "source": it["source"], "date": it["date"],
                   "origin": it["key"], "text": it["text"]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"saved {len(selected)} texts -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
