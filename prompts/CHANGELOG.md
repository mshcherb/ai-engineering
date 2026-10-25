# Prompt changelog

## v1 — 2026-10-20
Baseline. Short task description and field list, no labeling rules and no examples.
Purpose: a reference point to measure later versions against.

## v2 — 2026-10-25
Labeling rules from `data/LABELING.md` moved into the prompt. Each change targets an error of v1 on the golden set (`results/errors.md`, gpt-4o-mini t0: mention recall 65%, sentiment 53%):
- **Private companies listed explicitly** as mentions (`asset_type: private`, `ticker: null`): v1 skipped pre-IPO / private companies entirely.
- **What is not a mention** — countries, sectors, "the market", funds in general: v1 returned "Франция" and similar.
- **Sentiment = the author's own opinion**; a retold analyst recommendation or plain news → `neutral`; rules for 📈 / 📉 / 🤔 on earnings reports: v1 took an analyst "buy" for the author's view.
- **Any specific fund → `etf`**: v1 labeled listed funds as `private` / `other`.
- **`price_target` only for an explicit target** (not a company valuation), **`horizon` only if the holding period is stated**: v1 put a $2T valuation into `price_target` and guessed horizons.
- **`language`**: `mixed` only with full sentences in two languages, `unknown` without words: v1 called Russian texts with English tickers `mixed`.
- **Ticker format**: upper case, no `$`, JSON `null` rather than the string "null".

Examples in the prompt are deliberately not taken from the golden set, so the evaluation is not contaminated.

## v3 — 2026-10-25
v2 rules alone did not help gpt-4o-mini (mention F1 77% → 71%, sentiment 53% → 47%): the model ignored rules it saw only as text. v3 adds **4 few-shot examples** (made-up texts, none from the golden set) plus clarifications for the v2 errors that remained:
- **Fund holdings are mentions** ("the fund holds X, Y, Z"): v2 still skipped private companies listed as fund holdings (7 misses on one text).
- **Excluded company is still a mention** (`neutral`): v2 dropped "(нет, я не про $X)" altogether and returned the country instead. Example 1 shows a country that is not a mention.
- **`mixed` only for stated pros and cons of this security**; a question or a list of options → `neutral`: v2 labeled ETFs from a "which one should I pick?" question as `mixed`.
- **`language`**: a few words plus emoji still have a language; `unknown` only with no letters: v2 turned "X RIP 🪦" into `unknown`.
- **`price_target`**: per-share target (the author's or a quoted analyst's); yield is not a target.

Every example is checked against the schema when the prompt is built.
