"""Download the RAG corpus listed in data/corpus/sources.yaml.

SEC EDGAR requires a User-Agent with contact details and at most 10 requests/s:
set SEC_USER_AGENT="Your Name your@email" in .env.

Output: data/corpus/raw/<TICKER>_<kind>_<period>.<ext> + data/corpus/manifest.csv
Already downloaded files are skipped, so the script can be re-run safely.
PDFs from investor-relations sites are saved by hand (the sites block scripts); the script
lists the missing ones with their URLs.
"""
import csv
import hashlib
import os
import re
import sys
import time
from itertools import islice
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
RAW = CORPUS / "raw"
MANIFEST_FIELDS = ["doc_id", "ticker", "company", "kind", "form", "period", "filed",
                   "format", "url", "path", "sha256", "bytes"]
PAUSE_S = 0.2  # well under the 10 requests/s EDGAR limit


class Edgar:
    def __init__(self, user_agent: str):
        self.http = httpx.Client(headers={"User-Agent": user_agent}, timeout=60,
                                 follow_redirects=True)

    def get(self, url: str) -> httpx.Response:
        time.sleep(PAUSE_S)
        r = self.http.get(url)
        r.raise_for_status()
        return r

    def company(self, cik: int) -> dict:
        return self.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()

    def filings(self, cik: int):
        """All filings of a company, newest first.

        The main JSON holds only the latest ~1000; banks file thousands of prospectuses a year,
        so older pages are fetched lazily, only if the caller needs to go that far back.
        """
        d = self.company(cik)
        pages = [d["filings"]["recent"]]
        older = [f["name"] for f in d["filings"].get("files", [])]
        while pages:
            rec = pages.pop(0)
            yield from (dict(zip(rec, values)) for values in zip(*rec.values()))
            if not pages and older:
                pages.append(self.get(f"https://data.sec.gov/submissions/{older.pop(0)}").json())

    def exhibits(self, cik: int, accession: str) -> dict[str, tuple[str, int]]:
        """Exhibit type -> (URL, size in bytes), from the filing index page."""
        acc = accession.replace("-", "")
        index = self.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{accession}-index.htm").text
        found = {}
        for row in re.findall(r"<tr.*?</tr>", index, flags=re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
            href = re.search(r'href="([^"]+)"', row)
            if len(cells) >= 5 and href:
                kind, size = cells[3].strip(), cells[4].strip()
                url = "https://www.sec.gov" + href.group(1).replace("/ix?doc=", "")
                found.setdefault(kind, (url, int(size) if size.isdigit() else 0))
        return found


def doc_url(cik: int, f: dict) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accessionNumber'].replace('-', '')}/{f['primaryDocument']}"


def plan_documents(edgar: Edgar, ticker: str, spec: dict) -> list[dict]:
    """Pick the filings to download for one company."""
    cik = spec["cik"]
    name = edgar.company(cik)["name"]
    docs = []

    annual = islice((f for f in edgar.filings(cik) if f["form"] in ("10-K", "20-F")), spec.get("annual", 0))
    for f in annual:
        url, form = doc_url(cik, f), f["form"]
        # Some banks (WFC) file a thin 10-K and put the whole annual report into exhibit 13
        ex13 = edgar.exhibits(cik, f["accessionNumber"]).get("EX-13")
        if ex13 and ex13[1] > 2_000_000:
            url, form = ex13[0], f"{form} EX-13"
        docs.append({"ticker": ticker, "company": name, "kind": "annual", "form": form,
                     "period": f["reportDate"], "filed": f["filingDate"], "url": url})

    earnings = islice((f for f in edgar.filings(cik) if f["form"] == "8-K" and "2.02" in f["items"]),
                      spec.get("earnings", 0))
    for f in earnings:
        ex = edgar.exhibits(cik, f["accessionNumber"])
        found = ex.get("EX-99.1") or ex.get("EX-99")  # press release; TXN numbers it just EX-99
        if not found:
            print(f"  ! {ticker} {f['filingDate']}: no EX-99.1 in the 8-K, skipped")
            continue
        docs.append({"ticker": ticker, "company": name, "kind": "earnings", "form": "8-K EX-99.1",
                     "period": f["reportDate"], "filed": f["filingDate"], "url": found[0]})
    return docs


def save(http_get, doc: dict) -> dict:
    ext = Path(doc["url"].split("?")[0]).suffix.lower() or ".htm"
    doc_id = f"{doc['ticker']}_{doc['kind']}_{doc['period']}"
    path = RAW / f"{doc_id}{ext}"
    if not path.exists():
        path.write_bytes(http_get(doc["url"]).content)
        print(f"  + {path.name} ({path.stat().st_size // 1024} KB)")
    data = path.read_bytes()
    return {**doc, "doc_id": doc_id, "format": "pdf" if ext == ".pdf" else "html",
            "path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def main() -> None:
    load_dotenv(ROOT / ".env")
    ua = os.getenv("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        sys.exit('Set SEC_USER_AGENT="Your Name your@email" in .env (SEC EDGAR requires contact details)')
    sources = yaml.safe_load((CORPUS / "sources.yaml").read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    edgar = Edgar(ua)

    rows = []
    for ticker, spec in sources["companies"].items():
        print(ticker)
        for doc in plan_documents(edgar, ticker, spec):
            rows.append(save(edgar.get, doc))

    # IR-site PDFs: the sites block scripted downloads, so they are saved by hand
    missing = []
    for p in sources.get("pdf") or []:
        path = RAW / p["file"]
        if not path.exists():
            missing.append(p)
            continue
        data = path.read_bytes()
        rows.append({"doc_id": path.stem, "ticker": p["ticker"], "company": p["ticker"],
                     "kind": p["kind"], "form": "PDF", "period": p["period"], "filed": "",
                     "format": "pdf", "url": p["url"], "path": str(path.relative_to(ROOT)),
                     "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    if missing:
        print(f"\n{len(missing)} PDFs to save by hand into {RAW.relative_to(ROOT)}/:")
        for p in missing:
            print(f"  {p['file']}  <-  {p['url']}")

    with (CORPUS / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    total_mb = sum(r["bytes"] for r in rows) / 1e6
    print(f"\n{len(rows)} documents, {total_mb:.1f} MB -> data/corpus/manifest.csv")


if __name__ == "__main__":
    main()
