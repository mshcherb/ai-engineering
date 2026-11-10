# Judge calibration: judge_correct_v1 + judge_grounded_v1 (anthropic/claude-haiku-5.5)

| judge | n | agreement | false pass | false fail | disagreements |
|---|---|---|---|---|---|
| correct | 18 | 1.00 | 0.00 | 0.00 | — |
| grounded | 15 | 0.87 | 0.00 | 0.13 | l10, l13 |

## Disagreements

- **l10 grounded**: person True, judge False; unsupported: ['В третьем квартале 2026 года Tesla начала предоставлять поездки на Robotaxi с Киберкабами в Остине']
- **l13 grounded**: person True, judge False; unsupported: ['Выручка составила $6,055 миллиарда']
