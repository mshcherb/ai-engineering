# Judge calibration: judge_correct_v2 + judge_grounded_v2 (openai/gpt-4o-mini)

| judge | n | agreement | false pass | false fail | disagreements |
|---|---|---|---|---|---|
| correct | 18 | 0.83 | 0.06 | 0.11 | l04, l06, l07 |
| grounded | 15 | 0.93 | 0.07 | 0.00 | l06 |

## Disagreements

- **l04 correct**: person False, judge True: The key fact compared is the revenue for Texas Instruments in Q3 2026, which is $6.06 billion in the reference. The answer states $6,055 million, which is approximately $6.06 billion and matches the reference value.
- **l06 correct**: person True, judge False: The reference states that ASML's sales for 2025 were €32.7 billion, while the answer provides a figure of €32,667.3 million, which is approximately €32.7 billion but does not match the rounded figure exactly as stated in the reference.
- **l06 grounded**: person False, judge True; unsupported: []
- **l07 correct**: person True, judge False: The key fact compared is the net income of Wells Fargo in Q3 2026, which is $6.0 billion in the reference. The answer states approximately $5.95 billion, which does not match the reference value.
