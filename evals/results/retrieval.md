# Retrieval: 18 questions, k = 10

| chunking | mode | recall@5 | recall@10 | MRR@10 | p50, s |
|---|---|---|---|---|---|
| sections | vector | 0.61 | 0.72 | 0.50 | 0.1 |
| sections | vector + ticker filter | 0.61 | 0.72 | 0.50 | 0.33 |
| sections | bm25 | 0.61 | 0.72 | 0.53 | 0.02 |
| sections | bm25 + ticker filter | 0.61 | 0.72 | 0.54 | 0.02 |
| sections | hybrid | 0.67 | 0.89 | 0.54 | 0.15 |
| sections | hybrid + ticker filter | 0.67 | 0.89 | 0.52 | 0.34 |
| sections | hybrid+rerank | 1.00 | 1.00 | 0.81 | 2.67 |
| sections | hybrid+rerank + ticker filter | 1.00 | 1.00 | 0.81 | 2.79 |
| fixed | vector | 0.83 | 1.00 | 0.66 | 0.1 |
| fixed | vector + ticker filter | 0.83 | 1.00 | 0.66 | 0.28 |
| fixed | bm25 | 0.78 | 0.83 | 0.46 | 0.02 |
| fixed | bm25 + ticker filter | 0.78 | 0.83 | 0.47 | 0.02 |
| fixed | hybrid | 0.83 | 0.89 | 0.64 | 0.12 |
| fixed | hybrid + ticker filter | 0.83 | 0.94 | 0.65 | 0.29 |
| fixed | hybrid+rerank | 0.89 | 1.00 | 0.79 | 2.75 |
| fixed | hybrid+rerank + ticker filter | 0.89 | 1.00 | 0.79 | 2.83 |
