# Metrics

Golden set: 15 texts. valid / latency / cost — over all texts of a run; field accuracy — on matched mentions only; cost per 1000 docs, local model = $0 API.

| metric | gpt4o_mini_t0 | gpt4o_mini_t07 | llama32_3b_t0 | gpt4o_mini_t0 | gpt4o_mini_t07 | llama32_3b_t07 | gpt4o_mini_t0 | gpt4o_mini_t07 |
|---|---|---|---|---|---|---|---|---|
| model | openai/gpt-4o-mini | openai/gpt-4o-mini | llama3.2:3b | openai/gpt-4o-mini | openai/gpt-4o-mini | llama3.2:3b | openai/gpt-4o-mini | openai/gpt-4o-mini |
| prompt | v1 | v1 | v1 | v2 | v2 | v1 | v3 | v3 |
| temp/top_p | 0.0/1.0 | 0.7/0.9 | 0.0/1.0 | 0.0/1.0 | 0.7/0.9 | 0.7/0.9 | 0.0/1.0 | 0.7/0.9 |
| n | 49 | 49 | 49 | 49 | 49 | 49 | 49 | 49 |
| valid_% | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.0 | 100.0 | 100.0 |
| valid_first_try_% | 100.0 | 100.0 | 100.0 | 95.9 | 93.9 | 79.6 | 100.0 | 100.0 |
| repaired | 0 | 0 | 0 | 2 | 3 | 9 | 0 | 0 |
| failed+error | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| p50_s | 2.1 | 2.1 | 30.8 | 2.0 | 1.7 | 36.2 | 2.1 | 1.9 |
| p95_s | 6.6 | 6.8 | 89.8 | 7.4 | 8.7 | 137.5 | 6.4 | 7.2 |
| usd_per_1000 | 0.2 | 0.2 | 0.0 | 0.3 | 0.3 | 0.0 | 0.3 | 0.3 |
| about_stocks_% | 86.7 | 86.7 | 86.7 | 86.7 | 93.3 | 86.7 | 86.7 | 86.7 |
| language_% | 80.0 | 86.7 | 80.0 | 86.7 | 86.7 | 86.7 | 93.3 | 93.3 |
| mention_P_% | 94.4 | 94.4 | 63.6 | 93.8 | 88.2 | 85.7 | 100.0 | 100.0 |
| mention_R_% | 65.4 | 65.4 | 80.8 | 57.7 | 57.7 | 92.3 | 80.8 | 80.8 |
| mention_F1_% | 77.3 | 77.3 | 71.2 | 71.4 | 69.8 | 88.9 | 89.4 | 89.4 |
| ticker_% | 82.4 | 100.0 | 85.7 | 80.0 | 80.0 | 75.0 | 95.2 | 95.2 |
| sentiment_% | 52.9 | 52.9 | 38.1 | 46.7 | 46.7 | 33.3 | 66.7 | 71.4 |
| asset_type_% | 82.4 | 88.2 | 66.7 | 100.0 | 100.0 | 79.2 | 95.2 | 100.0 |
| horizon_% | 82.4 | 82.4 | 0.0 | 86.7 | 86.7 | 0.0 | 95.2 | 95.2 |
| price_target_% | 88.2 | 94.1 | 100.0 | 93.3 | 93.3 | 95.8 | 100.0 | 95.2 |
