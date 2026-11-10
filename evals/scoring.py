"""Numbers in English sources and Russian answers, compared by value instead of by string.

    numbers("$ 18,679 миллионов")         -> [{18679000000.0, 18679000.0}]
    fact_found("$18.68 billion", answer)   -> True when the answer has 18.68e9 up to rounding

The model copies numbers from English sources into Russian sentences, so the same fact comes as
"$6.06 billion", "$6,06 миллиарда", "$6,055 миллиарда" (a Russian decimal comma) or "$6,055 million".
A comma before exactly three digits is ambiguous, so such a number keeps both readings.
"""
import re

TOLERANCE = 0.005    # relative: "$54.2 billion" matches 54.23e9, 66.4% does not match 67.7%
# A reference is rounded too: "$3.5 billion" stands for $3,521 million, so a fact also allows half of
# its last digit (±0.05 billion here); "318,512" is exact, "68%" allows 67.5-68.5.

SCALES = [
    (r"trillion|трлн|триллион\w*", 1e12),
    (r"billion|bn|млрд|миллиард\w*", 1e9),
    (r"million|mn|млн|миллион\w*", 1e6),
    (r"thousand|тыс\.?|тысяч\w*", 1e3),
]
NUMBER_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[   ]\d{3})+|\d[\d,.]*\d|\d)(?![\d])")
SCALE_RE = re.compile(r"\s*(" + "|".join(p for p, _ in SCALES) + r")\b", re.I)
RANGE_GAP = 8        # "$52.3–54.3 billion", "от $52.3 до $54.3 млрд": the first number borrows the second one's scale


def readings(token: str) -> list[float]:
    """'6,055' -> [6055, 6.055]; '32,667.3' -> [32667.3]; '5,2' -> [5.2]; '318 512' -> [318512]."""
    token = re.sub(r"[   ]", "", token)
    if "," in token and "." in token:      # the last separator is the decimal one
        dec, thou = (".", ",") if token.rfind(".") > token.rfind(",") else (",", ".")
        return [float(token.replace(thou, "").replace(dec, "."))]
    if "," in token:
        parts = token.split(",")
        if all(len(p) == 3 for p in parts[1:]):
            values = [float(token.replace(",", ""))]
            if len(parts) == 2:
                values.append(float(token.replace(",", ".")))
            return values
        return [float(token.replace(",", "."))] if len(parts) == 2 else []
    try:
        return [float(token)]
    except ValueError:      # "1.2.3", a section number
        return []


def scale_of(word: str) -> float:
    return next(v for p, v in SCALES if re.fullmatch(p, word, re.I))


def numbers(text: str) -> list[set[float]]:
    """Every number of the text as the set of values it may mean, with its scale applied."""
    found = []
    for m in NUMBER_RE.finditer(text):
        values = readings(m.group(1))
        if not values:
            continue
        s = SCALE_RE.match(text, m.end())
        found.append({"values": values, "scale": scale_of(s.group(1)) if s else None,
                      "start": m.start(), "end": m.end()})
    out = []
    for i, n in enumerate(found):
        scales = {n["scale"] or 1.0}
        nxt = found[i + 1] if i + 1 < len(found) else None
        if n["scale"] is None and nxt and nxt["scale"] and nxt["start"] - n["end"] <= RANGE_GAP:
            scales.add(nxt["scale"])
        out.append({v * s for v in n["values"] for s in scales})
    return out


def value_of(fact: str) -> tuple[float, float]:
    """(value, rounding allowance) of a `must` fact, written the English way: '$50.2 billion', '318,512'."""
    if len(numbers(fact)) != 1:
        raise ValueError(f"a fact must hold exactly one number: {fact!r}")
    m = NUMBER_RE.search(fact)
    s = SCALE_RE.match(fact, m.end())
    scale = scale_of(s.group(1)) if s else 1.0
    decimals = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    return readings(m.group(1))[0] * scale, 0.5 * 10 ** -decimals * scale


def fact_found(fact: str, text: str) -> bool:
    target, allowance = value_of(fact)
    allowed = max(allowance, TOLERANCE * abs(target))
    return any(abs(v - target) <= allowed for values in numbers(text) for v in values)
