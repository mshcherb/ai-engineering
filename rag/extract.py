"""Turn raw corpus files into a list of structural blocks.

A block is one of:
    {"type": "heading", "level": 1|2, "text": ...}   1 = "Item 7. ..." / document part, 2 = sub-heading
    {"type": "text", "text": ...}                     one paragraph
    {"type": "table", "text": ...}                    a markdown table
    {"type": "page", "number": n}                     PDF page break (keeps page numbers for citations)

Based on the lesson 6 ingestion practice, adapted to SEC EDGAR filings (inline XBRL HTML with
inline styles instead of <h1>/<h2>) and investor-relations PDFs.
"""
import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from pypdf import PdfReader

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

ITEM_RE = re.compile(r"^(item|part)\s+[0-9IVX]+[A-Z]?\.?\s", re.IGNORECASE)
CHECKBOX_RE = re.compile("[\u2610\u2611\u2612]")  # cover-page checkboxes: "Item 17 ☐ Item 18 ☒"
BLOCK_TAGS = ("div", "p", "table")
MAX_HEADING_CHARS = 150


def clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("​", "")
    return " ".join(text.split())


def is_bold(el: Tag) -> bool:
    """EDGAR marks headings with inline styles: every piece of text in the block is bold."""
    pieces = [s for s in el.find_all(string=True) if s.strip()]
    if not pieces:
        return False
    for s in pieces:
        node, bold = s.parent, False
        while node is not None and node is not el.parent:
            style = (node.get("style") or "").replace(" ", "").lower()
            if node.name in ("b", "strong") or "font-weight:700" in style or "font-weight:bold" in style:
                bold = True
                break
            node = node.parent
        if not bold:
            return False
    return True


def table_to_markdown(table: Tag) -> str:
    """EDGAR tables use spacer cells and split "$ | 1,234" and "(12 | )" into separate cells."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
        merged: list[str] = []
        for c in cells:
            if not c:
                continue
            if merged and (merged[-1] in ("$", "(", "$(") or c in (")", "%", ")%")):
                merged[-1] += c  # "$" + "1,234" -> "$1,234"; "(12" + ")" -> "(12)"
            else:
                merged.append(c)
        if merged:
            rows.append(merged)
    if not rows:
        return ""
    if len(rows) == 1 and len(rows[0]) == 1:  # a one-cell "table" is just a styled paragraph
        return rows[0][0]
    width = max(len(r) for r in rows)
    lines = ["| " + " | ".join(r + [""] * (width - len(r))) + " |" for r in rows]
    lines.insert(1, "|" + " --- |" * width)
    return "\n".join(lines)


def extract_html(path: Path) -> list[dict]:
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(re.compile(r"^ix:header$", re.I)):
        tag.decompose()  # hidden XBRL facts, not part of the visible document
    for tag in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        tag.decompose()

    blocks: list[dict] = []
    body = soup.body or soup
    for el in body.find_all(BLOCK_TAGS):
        if el.find_parent("table"):
            continue  # its text is part of the table block
        if el.name == "table":
            md = table_to_markdown(el)
            if md.startswith("|"):
                blocks.append({"type": "table", "text": md})
            elif md:
                blocks.append({"type": "text", "text": md})
            continue
        if el.find(BLOCK_TAGS):
            continue  # not a leaf block: its children are visited on their own
        text = clean(el.get_text(" "))
        if not text or re.fullmatch(r"[\d\s\-–|]+|Table of Contents", text, flags=re.I):
            continue  # empty blocks, page numbers, "Table of Contents" back-links
        if len(text) <= MAX_HEADING_CHARS and ITEM_RE.match(text) and not CHECKBOX_RE.search(text):
            blocks.append({"type": "heading", "level": 1, "text": text})
        elif (len(text) <= MAX_HEADING_CHARS and is_bold(el) and text[0].isupper()
              and not text.endswith((".", ",", ";"))):
            # a bold line starting in lower case is a fragment of a layout box, not a heading
            blocks.append({"type": "heading", "level": 2, "text": text})
        elif continues(blocks, text):
            blocks[-1]["text"] += " " + text
        else:
            blocks.append({"type": "text", "text": text})
    return blocks


def continues(blocks: list[dict], text: str) -> bool:
    """A paragraph broken into several blocks: by a page break (banks) or into one block per
    visual line (ASML's annual report is a brochure converted to HTML). The previous block does
    not end a sentence and this one starts in lower case."""
    if not blocks or blocks[-1]["type"] != "text":
        return False
    prev = blocks[-1]["text"]
    return not prev.endswith((".", "!", "?", ":", ";")) and (text[:1].islower() or text[:1] in ",;)")


ROMAN_HEADING = re.compile(r"^[IVX]+\.\s+\S")            # "I.  Revenue Analysis"
PAGE_LINE = re.compile(r"^(page\s*)?\d+(\s*(of|/)\s*\d+)?$", re.IGNORECASE)
BULLET = re.compile(r"^(l|•|▪|-)\s+")                     # TSMC's bullet glyph comes out as "l "


NUMERIC = re.compile(r"[-(]?(NT|US)?\$?[\d,.]+[%)]*|\d+Q\d+|\d+nm", re.IGNORECASE)


def is_table_row(line: str) -> bool:
    """A row of a numeric table: mostly numbers ("3nm 33% 30% 23%"), not prose with a few figures."""
    tokens = line.split()
    nums = sum(1 for t in tokens if NUMERIC.fullmatch(t))
    return nums >= 2 and nums / len(tokens) >= 0.4


def extract_pdf(path: Path) -> list[dict]:
    """PDF text per page -> headings, paragraphs and table rows.

    PDFs have no styles, so structure comes from the lines themselves (lesson 6 rules):
    lines repeated on most pages are running headers/footers; a line that does not end a
    sentence continues on the next line; consecutive numeric lines form a table.
    """
    reader = PdfReader(path)
    pages = [[clean(ln) for ln in (pg.extract_text() or "").split("\n")] for pg in reader.pages]
    def key(ln: str) -> str:  # footers differ only by the page number: "© 3 2026 TSMC" / "© 4 2026 TSMC"
        return re.sub(r"\d+", "#", ln)

    counts: dict[str, int] = {}
    for lines in pages:
        for k in {key(ln) for ln in lines if ln}:
            counts[k] = counts.get(k, 0) + 1
    repeated = {k for k, n in counts.items() if len(pages) > 2 and n > len(pages) / 2}
    slides = "presentation" in path.stem

    blocks: list[dict] = []
    for number, lines in enumerate(pages, 1):
        blocks.append({"type": "page", "number": number})
        lines = [ln for ln in lines if ln and key(ln) not in repeated and not PAGE_LINE.match(ln)
                 and not re.search(r"\bPage \d+$", ln)]
        if slides and lines:  # one slide = one page; its first line is the slide title
            blocks.append({"type": "heading", "level": 2, "text": lines.pop(0)})
        para: list[str] = []
        rows: list[str] = []

        def flush() -> None:
            if para:
                blocks.append({"type": "text", "text": " ".join(para)})
                para.clear()
            if rows:
                blocks.append({"type": "table", "text": "\n".join(rows)})
                rows.clear()

        for ln in lines:
            if ROMAN_HEADING.match(ln) and len(ln) < 80:
                flush()
                blocks.append({"type": "heading", "level": 1, "text": ln})
            elif len(ln) < 60 and ln.endswith(":") and ln[0].isupper():
                flush()
                blocks.append({"type": "heading", "level": 2, "text": ln.rstrip(":")})
            elif is_table_row(ln):
                if para:
                    flush()
                rows.append(ln)
            elif BULLET.match(ln):
                flush()
                para.append("- " + BULLET.sub("", ln))
            else:
                if rows:
                    flush()
                if para and para[-1].endswith((".", "!", "?")) and ln[:1].isupper():
                    flush()
                if para and para[-1].endswith("-"):
                    para[-1] += ln  # "quarter-" + "over-quarter": a compound word wrapped at its hyphen
                else:
                    para.append(ln)
        flush()
    return blocks


def extract(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix in (".htm", ".html"):
        return extract_html(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    raise ValueError(f"unsupported file type: {suffix}")
