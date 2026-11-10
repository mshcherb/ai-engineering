# Retrieval: 18 questions, k = 10

| chunking | query | mode | recall@5 | recall@10 | MRR@10 | p50, s |
|---|---|---|---|---|---|---|
| sections | RU as is | vector | 0.00 | 0.11 | 0.01 | 0.13 |
| sections | RU as is | bm25 | 0.06 | 0.17 | 0.03 | 0.01 |
| sections | RU as is | hybrid | 0.00 | 0.00 | 0.00 | 0.13 |
| sections | RU as is | hybrid+rerank | 0.06 | 0.11 | 0.06 | 2.76 |
| sections | RU→EN (LLM) | vector | 0.72 | 0.78 | 0.54 | 0.11 |
| sections | RU→EN (LLM) | bm25 | 0.44 | 0.50 | 0.35 | 0.03 |
| sections | RU→EN (LLM) | hybrid | 0.61 | 0.78 | 0.44 | 0.14 |
| sections | RU→EN (LLM) | hybrid+rerank | 0.89 | 0.89 | 0.69 | 2.57 |
| sections | RU→EN + LLM filters | vector | 0.78 | 0.89 | 0.67 | 0.31 |
| sections | RU→EN + LLM filters | bm25 | 0.61 | 0.83 | 0.45 | 0.03 |
| sections | RU→EN + LLM filters | hybrid | 0.78 | 0.94 | 0.60 | 0.32 |
| sections | RU→EN + LLM filters | hybrid+rerank | 1.00 | 1.00 | 0.76 | 2.63 |
| sections | EN reference | vector | 0.61 | 0.72 | 0.50 | 0.12 |
| sections | EN reference | bm25 | 0.61 | 0.72 | 0.53 | 0.03 |
| sections | EN reference | hybrid | 0.67 | 0.89 | 0.54 | 0.14 |
| sections | EN reference | hybrid+rerank | 1.00 | 1.00 | 0.81 | 2.55 |
| sections | EN + ticker filter | vector | 0.61 | 0.72 | 0.50 | 0.3 |
| sections | EN + ticker filter | bm25 | 0.61 | 0.72 | 0.54 | 0.02 |
| sections | EN + ticker filter | hybrid | 0.67 | 0.89 | 0.52 | 0.31 |
| sections | EN + ticker filter | hybrid+rerank | 1.00 | 1.00 | 0.81 | 2.67 |
| fixed | RU as is | vector | 0.22 | 0.33 | 0.11 | 0.12 |
| fixed | RU as is | bm25 | 0.17 | 0.22 | 0.07 | 0.01 |
| fixed | RU as is | hybrid | 0.22 | 0.39 | 0.09 | 0.13 |
| fixed | RU as is | hybrid+rerank | 0.00 | 0.06 | 0.01 | 2.82 |
| fixed | RU→EN (LLM) | vector | 0.83 | 0.89 | 0.71 | 0.07 |
| fixed | RU→EN (LLM) | bm25 | 0.44 | 0.56 | 0.34 | 0.02 |
| fixed | RU→EN (LLM) | hybrid | 0.67 | 0.89 | 0.51 | 0.12 |
| fixed | RU→EN (LLM) | hybrid+rerank | 0.89 | 0.89 | 0.73 | 2.65 |
| fixed | RU→EN + LLM filters | vector | 0.83 | 0.94 | 0.77 | 0.26 |
| fixed | RU→EN + LLM filters | bm25 | 0.83 | 0.83 | 0.48 | 0.02 |
| fixed | RU→EN + LLM filters | hybrid | 0.83 | 0.83 | 0.66 | 0.29 |
| fixed | RU→EN + LLM filters | hybrid+rerank | 0.94 | 0.94 | 0.82 | 2.71 |
| fixed | EN reference | vector | 0.83 | 1.00 | 0.66 | 0.11 |
| fixed | EN reference | bm25 | 0.78 | 0.83 | 0.46 | 0.03 |
| fixed | EN reference | hybrid | 0.83 | 0.89 | 0.64 | 0.09 |
| fixed | EN reference | hybrid+rerank | 0.89 | 1.00 | 0.79 | 2.81 |
| fixed | EN + ticker filter | vector | 0.83 | 1.00 | 0.66 | 0.25 |
| fixed | EN + ticker filter | bm25 | 0.78 | 0.83 | 0.47 | 0.02 |
| fixed | EN + ticker filter | hybrid | 0.83 | 0.94 | 0.65 | 0.27 |
| fixed | EN + ticker filter | hybrid+rerank | 0.89 | 1.00 | 0.79 | 2.74 |

## Query rewriting (rewrite_v1, openai/gpt-4o-mini)

Tickers right: 18/18; filters keep a relevant chunk: 18/18; errors: 0; cost per 1000 questions: $0.119

| id | query_en | tickers | filters | keeps answer |
|---|---|---|---|---|
| r01 | What was JPMorgan's net revenues for the third quarter of 2026? | JPM | ticker=['JPM'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r02 | What was JPMorgan Chase's net revenues in the second quarter of 2026? | JPM | ticker=['JPM'], period_from=2026-06-30, period_to=2026-09-13 | yes |
| r03 | What was JPMorgan's CET1 capital ratio at the end of the third quarter of 2026? | JPM | ticker=['JPM'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r04 | What was Goldman Sachs' net revenues in the third quarter of 2026? | GS | ticker=['GS'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r05 | What was Citigroup's net income for the third quarter of 2026 according to their report? | C | ticker=['C'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r06 | What was the net income of Bank of America's Consumer Banking segment in the third quarter of 2026? | BAC | ticker=['BAC'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r07 | How much did AWS sales grow compared to last year in the third quarter of 2026? | AMZN | ticker=['AMZN'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r08 | What was Micron's revenue for the fourth quarter of fiscal year 2026? | MU | ticker=['MU'] | yes |
| r09 | What were Texas Instruments' net revenues and diluted EPS in the third quarter of 2026? | TXN | ticker=['TXN'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r10 | What was NVIDIA's data center revenue in the second quarter of fiscal year 2027? | NVDA | ticker=['NVDA'] | yes |
| r11 | How much did NVIDIA incur in costs due to American export restrictions to China? | NVDA | ticker=['NVDA'] | yes |
| r12 | What is TSMC's gross margin for the third quarter of 2026? | TSM | ticker=['TSM'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r13 | What revenue forecast does TSMC promise for the fourth quarter of 2026? | TSM | ticker=['TSM'] | yes |
| r14 | What was the revenue share of TSMC's HPC segment in the third quarter of 2026? | TSM | ticker=['TSM'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r15 | How many employees did JPMorgan Chase have at the end of 2025? | JPM | ticker=['JPM'], period_from=2025-12-31, period_to=2026-03-16 | yes |
| r16 | What does Tesla report about Cybertruck in the third quarter of 2026? | TSLA | ticker=['TSLA'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r17 | What was Wells Fargo's net income in the third quarter of 2026? | WFC | ticker=['WFC'], period_from=2026-09-30, period_to=2026-12-14 | yes |
| r18 | What were ASML's sales for 2025? | ASML | ticker=['ASML'], period_from=2025-12-31, period_to=2026-03-16 | yes |
