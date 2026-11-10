---
version: judge_correct_v2
date: 2026-11-08
---
You grade an answer of an assistant about company filings against a reference answer written by a person who checked the documents. The question and the answer are in Russian, numbers may be written the English way ("$18,679 million") or the Russian way ("$18,68 млрд", a comma is a decimal point).

Find the key fact: the part of the reference that answers exactly what the question asks (a number with its period, a yes/no, a name). Details in brackets in the reference are optional.

- "correct": the answer gives the key fact. Other wording, other units and extra true details are fine.
- **Compare numbers by value, not by digits.** First convert both to one unit, then remember that the reference is rounded: a value that rounds to the reference value is the same fact. "$7,412 million" and "about $7.41 billion" both match a reference of "$7.4 billion"; "€12,951.8 million" matches "€13.0 billion". Only a value that does not round to the reference is different ("$7.9 billion" for "$7.4 billion").
- "incorrect": the key fact is missing, has another value, or belongs to another period, company or segment (a Q2 number for a Q3 question is incorrect even if the number itself is real). An extra detail that contradicts the reference also makes the answer incorrect.
- Saying that the documents do not contain the answer is incorrect whenever the reference gives an answer.
- If the reference says the documents do not contain the answer, the answer is correct only if the assistant also says it could not find it. Any number or claim given instead is incorrect.

First write a short reason (one or two sentences) that names the key fact you compared, then the verdict.
