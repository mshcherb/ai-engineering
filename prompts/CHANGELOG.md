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

# HW2: query rewriting prompts (`rag/rewrite.py`)

## rewrite_v1 — 2026-11-08
A Russian question → `{query_en, tickers, period}` (structured output, gpt-4o-mini, t = 0).
- The corpus, the embedding model and BM25 are English-only, so the question is rewritten into the wording a filing uses: the company's official name, the standard metric name, the period in full words.
- The list of corpus companies with tickers is inserted at run time from `chunks.jsonl` (`{companies}`), so slang and Cyrillic names map to the right ticker.
- `period` is only year / quarter / fiscal; the code turns it into a date range (the model does not compute dates). Fiscal periods and forecasts get no date filter.
- 5 made-up examples, none from `evals/retrieval_questions.jsonl`.

## rewrite_v2 — 2026-11-08
v1 turned «Киберкаб» into "Cybertruck" (r16): it swapped a Cyrillic product name for a better-known product of the same company. Retrieval did not suffer (the ticker and period filters kept the right release), but an answer built on that query would be about the wrong product.
- Rule: names of products, projects and segments are transliterated letter by letter, never replaced by a similar-sounding product.
- One more made-up example (Amazon, «Кайпер» → "Kuiper").

Note: the fix was prompted by an error on a test question (r16), so the gain on r16 is not an independent measurement; the example is deliberately about another company and product.

**Result: rejected, `config.yaml` stays on rewrite_v1.** On the 18 retrieval questions (sections, hybrid + rerank, with LLM filters) recall@5 fell 1.00 → 0.94, MRR 0.76 → 0.69:
- r16 is still "Cybertruck": gpt-4o-mini ignores the rule for a product it knows much better than "Cybercab".
- r13 broke: "прогноз на Q4 2026" now gets period Q4 2026 (v1: null), the date filter drops the Q3 report that holds the forecast. A longer prompt shifted the model on a rule that had nothing to do with the change.
Lesson: a prompt change is checked on the whole set, not only on the question it targets. A safer fix for both is in code, not in the prompt (step 3): retry without the period filter when the filtered search returns nothing, and pass the original Russian question to the answering model.

# HW2: answer prompts (`rag/answer.py`)

## answer_v1 — 2026-11-08
Answer only from the retrieved chunks, in Russian, structured output `{found, answer, citations}`. Based on the lesson 9 `v2` system prompt, adapted to filings:
- A label `[Sn]` after **every** claim (the assignment asks for a source per statement); the code checks the labels and renders them as "document + section".
- `found: false` with a short "what is missing" when the sources do not answer; the code then shows the fixed "не знаю" text. Similar metric or another period is explicitly not an answer (version traps: Q2 vs Q3 releases, 10-K 2024 vs 2025).
- The release date vs quarter rule: the `period` of a US earnings release is its release date.
- Numbers copied as written, no computed numbers without cited inputs; product names in Latin letters (lesson from rewrite_v1: «Киберкаб» → "Cybertruck").

## answer_v2 — 2026-11-08
Errors of v1 on the 20 retrieval questions (`evals/results/answers_sample_answer_v1.md`, 17/18 answered, 2/2 "не знаю" right):
- **r04 "$ 18,679 млн"** (should be $18.68 billion): the v1 rule "$50.2 billion → $50,2 млрд" made the model mix English and Russian separators, so a number read as 18.7 *million*. v2: numbers stay in the source's format ("$18,679 million"), no unit conversion, no separator swap.
- **r03 "нет данных о CET1"** although the chunk was S1: a flattened table row (`label footnote Std. value | Adv. value`) looked like "not the metric". v2 explains the flattened-table format with a made-up example (net interest margin), not the test row.
- **r16** a fact sentence without a label (one label at the end of two sentences). v2: the label goes after every sentence with a fact, repeated if needed.

# HW2: judge prompts (`evals/judge.py`)

Calibrated on 18 answers labelled by hand (`evals/labels.jsonl`: 9 bot answers + 9 edited ones; correct 18, grounded 15, "не знаю" has no claims): `python -m evals.judge --calibrate --run <run> --correct-prompt ... --grounded-prompt ...`. Results in `evals/results/calibration_*.md`.

| judge model | prompts | correct | grounded | notes |
|---|---|---|---|---|
| gpt-4o-mini | v1 / v1 | 0.89 | 0.93 | false fail l06, l07 (units / rounding: "€32,667.3 million" ≠ "€32.7 billion"); **false pass l06** grounded (a real number of another line) |
| gpt-4o-mini | v2 / v2 | 0.83 | 0.93 | the units rule did not help, and l04 broke (answer without EPS passed): a longer prompt shifts a small model |
| claude-haiku-5.5 | v1 / v1 | 1.00 | 0.93, 0.87, 0.87 | 3 runs; disagreements only false fails: l13 "$6,055 миллиарда" (Russian decimal comma), l10 (paraphrase) |
| claude-haiku-5.5 | v1 / v3 | 1.00 | 0.93, 0.87, 0.87, 0.93 | same as v1 within the run-to-run noise |

- judge_correct_v1, judge_grounded_v1 — 2026-11-08: correct = key fact of the reference, another period/segment is incorrect; grounded = claims only from the answer, a detail is a claim of its own, the source header (document, period, section) is passed with the chunk text.
- judge_correct_v2 — compare numbers by value after unit conversion, the reference is rounded (made-up examples). No gain.
- judge_grounded_v2 — "a number belongs to its line" (metric, segment, period). No gain on gpt-4o-mini; haiku catches l06 without it.
- judge_grounded_v3 — v2 + Russian decimal comma rule. Within noise of v1.

**Chosen: claude-haiku-5.5 + judge_correct_v1 + judge_grounded_v1** (simplest prompts, v2/v3 gave no measured gain). Another family than the bot (gpt-4o-mini) also avoids a model grading itself. Its errors are false fails (stricter than a person), never false passes on this set.
