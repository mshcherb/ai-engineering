# Judge calibration: judge_correct_v1 + judge_grounded_v3 (anthropic/claude-haiku-5.5)

| judge | n | agreement | false pass | false fail | disagreements |
|---|---|---|---|---|---|
| correct | 18 | 1.00 | 0.00 | 0.00 | — |
| grounded | 15 | 0.93 | 0.00 | 0.07 | l10 |

## Disagreements

- **l10 grounded**: person True, judge False; unsupported: ['Tesla начала предоставлять поездки на Robotaxi с использованием Киберкабов']
