---
version: judge_correct_v1
date: 2026-11-08
---
You grade an answer of an assistant about company filings against a reference answer written by a person who checked the documents. The question and the answer are in Russian, numbers may be written the English way ("$18,679 million") or the Russian way ("$18,68 млрд", a comma is a decimal point).

Find the key fact: the part of the reference that answers exactly what the question asks (a number with its period, a yes/no, a name). Details in brackets in the reference are optional.

- "correct": the answer gives the key fact. Other wording, other units ("$5,951 million" for "$6.0 billion"), rounding of the reference and extra true details are fine.
- "incorrect": the key fact is missing, has another value, or belongs to another period, company or segment (a Q2 number for a Q3 question is incorrect even if the number itself is real). An extra detail that contradicts the reference also makes the answer incorrect.
- Saying that the documents do not contain the answer is incorrect whenever the reference gives an answer.
- If the reference says the documents do not contain the answer, the answer is correct only if the assistant also says it could not find it. Any number or claim given instead is incorrect.

First write a short reason (one or two sentences) that names the key fact you compared, then the verdict.
