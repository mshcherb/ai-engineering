# Judge calibration: judge_correct_v1 + judge_grounded_v1 (openai/gpt-4o-mini)

| judge | n | agreement | false pass | false fail | disagreements |
|---|---|---|---|---|---|
| correct | 18 | 0.89 | 0.00 | 0.11 | l06, l07 |
| grounded | 15 | 0.93 | 0.07 | 0.00 | l06 |

## Disagreements

- **l06 correct**: person True, judge False: The key fact compared is the total net sales of ASML for 2025, which is stated as €32.7 billion in the reference. The answer provides a different figure of €32,667.3 million, which does not match the reference value.
- **l06 grounded**: person False, judge True; unsupported: []
- **l07 correct**: person True, judge False: The key fact compared is the net income of Wells Fargo in Q3 2026, which is stated as $6.0 billion in the reference. The answer provides a different value of approximately $5.95 billion, which does not match the reference.
