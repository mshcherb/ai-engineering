# Ответы для ручной разметки (evals/labels.jsonl)

Для каждого `lNN` поставьте в `evals/labels.jsonl` два поля:

- `correct`: `true` / `false` — ответ даёт ключевой факт эталона (для вопросов без ответа — правильно, только если бот сказал «не знаю»).
- `grounded`: `true` / `false` — **каждое** утверждение ответа есть в процитированных источниках ниже (неважно, правильный ли это ответ на вопрос). Для «В документах этого нет» оставьте `null`.
- `note`: по желанию, почему.

Часть ответов настоящие (бот), часть я испортил вручную — поле `made`, но оценивайте по тексту, а не по полю.

## l01 — r15 (version_trap)

**Вопрос:** Сколько сотрудников было у JPMorgan Chase на конец 25 года?

**Эталон:** На конец 2025 года у JPMorgan Chase было 318,512 сотрудников.

**Ответ:** На конец 2025 года у JPMorgan Chase было 317,233 сотрудника [S1].

<details><summary>Источник 1: JPM_annual_2025-12-31#34 · Item 1. Business. > Human capital</summary>

```
JPMorganChase believes that its long-term growth and success depend on its ability to identify, attract, develop, retain and engage talented employees and foster an inclusive work environment. The information provided below relates to JPMorganChase’s full-time and part-time employees and does not include the Firm’s contractors.

Global workforce

As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S. The following table presents the distribution of the Firm’s global workforce by region and by line of business (“LOB”) and Corporate as of December 31, 2025:

| Employee Breakdown by Region | Employee Breakdown by LOB and Corporate | | |
| --- | --- | --- | --- |
| Region | Employees | LOB | Employees |
| North America | 185,208 | CCB | 144,196 |
| Asia-Pacific | 96,499 | CIB | 94,563 |
| Europe/Middle East/Africa | 31,030 | AWM | 29,722 |
| Latin America/Caribbean | 5,775 | Corporate | 50,031 |
| Total Firm | 318,512 | Total Firm | 318,512 |

Workforce composition
```

</details>

## l02 — r10 (fact)

**Вопрос:** Какая была выручка сегмента дата центр у нвидиа во втором квартале 2027 финансового года?

**Эталон:** Выручка сегмента Data Center NVIDIA во 2 кв. 2027 фин. года — $89.0 млрд.

**Ответ:** Выручка сегмента Data Center во втором квартале финансового года 2027 составила $89.0 billion, что на 117% больше по сравнению с прошлым годом [S1].

<details><summary>Источник 1: NVDA_earnings_2026-08-26#0 · NVIDIA Announces Financial Results for Second Quarter Fiscal 2027</summary>

```
• Revenue of $96.2 billion, up 106% from a year ago

• Data Center revenue of $89.0 billion, up 117% from a year ago

SANTA CLARA, Calif.—Aug. 26, 2026― NVIDIA (NASDAQ: NVDA) today reported revenue for the second quarter ended July 26, 2026, of $96.2 billion, up 18% from the previous quarter and up 106% from a year ago. For the quarter, GAAP and non-GAAP gross margins were both 75.0%. GAAP and non-GAAP earnings per diluted share were $2.46 and $2.22, respectively.

“AI has reached its inflection point. It’s doing useful work. Its tokens are productive and profitable. Now, compute is revenue,” said Jensen Huang, founder and CEO of NVIDIA. “And demand is accelerating. This time last year, one lab alone was driving the buildout; today, we have a golden age of new AI labs and startups, multiple frontier labs scaling in parallel, a thriving open-model ecosystem and physical AI coming online — with strong momentum across the U.S. and around the world. The AI infrastructure buildout is at full steam. Vera Rubin, now in full production, was built to power exactly this moment.”

During the second quarter of fiscal 2027, NVIDIA returned approximately $26.0 billion to shareholders in the form of shares repurchased and cash dividends. As of the end of the second quarter, the company had approximately $99.0 billion remaining under its share repurchase authorization.

NVIDIA will pay its next quarterly cash dividend of $0.25 per share on October 1, 2026, to all shareholders of record on September 10, 2026.
```

</details>

## l03 — r01 (version_trap)

**Вопрос:** Какую выручку показал JPMorgan в третьем квартале 2026 года?

**Эталон:** Выручка JPMorgan (reported) в 3 кв. 2026 — $50.2 млрд.

**Ответ:** Выручка JPMorgan в третьем квартале 2026 года составила $57.3 billion [S1].

<details><summary>Источник 1: JPM_earnings_2026-10-13#3 · THIRD-QUARTER 2026 RESULTS 1</summary>

```
| Firmwide Metrics | n | Reported revenue of $50.2 billion and managed revenue 2 of $50.9 billion |
| --- | --- | --- |
| n | Average loans up 20% YoY and 6% QoQ; average deposits up 5% YoY, down 3% QoQ | |
```

</details>

## l04 — r09 (fact)

**Вопрос:** Какие были выручка и прибыль на акцию у Texas Instruments в третьем квартале 2026?

**Эталон:** Texas Instruments в 3 кв. 2026: выручка $6.06 млрд, прибыль на акцию $2.62 (чистая прибыль $2.43 млрд).

**Ответ:** Выручка Texas Instruments в третьем квартале 2026 года составила $6,055 million [S1].

<details><summary>Источник 1: TXN_earnings_2026-10-21#4 · TEXAS INSTRUMENTS INCORPORATED AND SUBSIDIARIES</summary>

```
| Consolidated Statements of Income | For Three Months Ended September 30, | |
| --- | --- | --- |
| (In millions, except per-share amounts) | 2026 | 2025 |
| Revenue | $6,055 | $4,742 |
| Cost of revenue (COR) | 2,168 | 2,019 |
| Gross profit | 3,887 | 2,723 |
| Research and development (R&D) | 530 | 518 |
| Selling, general and administrative (SG&A) | 476 | 457 |
| Acquisition charges | 7 | — |
| Restructuring charges/other | — | 85 |
| Operating profit | 2,874 | 1,663 |
| Other income (expense), net (OI&E) | 72 | 62 |
| Interest and debt expense | 141 | 141 |
| Income before income taxes | 2,805 | 1,584 |
| Provision for income taxes | 380 | 220 |
| Net income | $2,425 | $1,364 |
| Diluted earnings per common share | $2.62 | $1.48 |
| Average shares outstanding: | | |
| Basic | 914 | 909 |
| Diluted | 921 | 914 |
| Cash dividends declared per common share | $1.42 | $1.36 |
| Supplemental Information (Quarterly, except as noted) | | |
| Provision for income taxes is based on the following: | | |
| Operating taxes (calculated using the estimated annual effective tax rate) | $390 | $249 |
| Discrete tax items | (10) | (29) |
| Provision for income taxes (effective taxes) | $380 | $220 |
```

</details>

## l05 — r19 (no_answer)

**Вопрос:** Какую выручку Apple показал в третьем квартале 2026?

**Эталон:** В документах этого нет: Apple нет в корпусе.

**Ответ:** В документах этого нет.

_Источников нет: бот ответил «не знаю»._

## l06 — r18 (fact)

**Вопрос:** Какие были продажи ASML за 2025 год?

**Эталон:** Продажи (total net sales) ASML за 2025 год — €32.7 млрд.

**Ответ:** Общие продажи ASML за 2025 год составили €32,667.3 миллиона, что на €4.4 миллиарда больше, чем в 2024 году, что соответствует росту на 15.6% [S6]. Продажи систем увеличились на €2.9 миллиарда, в то время как продажи в сегменте памяти снизились на €0.2 миллиарда [S1].

<details><summary>Источник 1: ASML_annual_2025-12-31#982 · Revenue recognition – Identification of distinct performance obligations in volume purchase agreements</summary>

```
As disclosed by management, net sales were EUR 32,667.3 million for the year ended December 31, 2025. As described in Note 2 to the consolidated financial statements, the main portion of net sales are entered into with customers under volume purchase agreements (“VPAs”) that have multiple performance obligations, which mainly include sales of systems, system-related options, installation, training, and extended and enhanced warranties.

| STRATEGIC REPORT | CORPORATE GOVERNANCE | SUSTAINABILITY | FINANCIALS | ASML Annual Report 2025 | 275 |
| --- | --- | --- | --- | --- | --- |

| Financial statements | Notes | Appendices | Definitions |
| --- | --- | --- | --- |

Report of independent registered public accounting firm (continued)

The principal considerations for our determination that performing procedures relating to revenue recognition – identification of distinct performance obligations in volume purchase agreements is a critical audit matter are a high degree of auditor subjectivity and effort in performing procedures and evaluating the sufficiency and appropriateness of audit evidence related to the identification of distinct performance obligations in material VPAs.

Addressing the matter involved performing procedures and evaluating audit evidence in connection with forming our overall opinion on the consolidated financial statements. These procedures included testing the effectiveness of controls relating to the Company’s revenue recognition process related to the identification of distinct performance obligations included in VPAs. These procedures also included, among others, (i) evaluating the identification of distinct performance obligations of material VPAs by obtaining and reading the agreement as well as relevant amendments and underlying accounting analysis and considering the specific terms, conditions, and promises introduced; and (ii) the identification of circumstances which may trigger the identification of additional performance obligations.

/s/ PricewaterhouseCoopers Accountants N.V.

Eindhoven, The Netherlands

February 25, 2026

We have served as the Company’s auditor since 2024 .
```

</details>

<details><summary>Источник 2: ASML_annual_2025-12-31#154 · Total net sales</summary>

```
In 2025 , total net sales increased by €4.4 billion , representing a 15.6% year-over-year increase. This growth was driven by a 12.4% increase in net system sales and a 26.2% increase in net service and field option sales compared to 2024 .

Total net sales growth (in billions)

In Logic, net sales increased by €2.9 billion , primarily driven by leading-edge foundry growth in support of strong AI demand and our customers building capacity for their next nodes .

In Memory, net sales decreased by €0.2 billion , primarily reflecting a continuation of high Memory demand following strong growth in 2024. This momentum is fueled by investment in high-bandwidth memory and

DDR5 to support AI-related applications, which remain a key growth driver in the Memory market.

Net service and field option sales increased mainly due to the growing installed base of systems , higher levels of lithography tool use for certain customers, and more NXE field upgrades .
```

</details>

## l07 — r17 (similar_docs)

**Вопрос:** Сколько сделал Wells Fargo чистыми в третьем квартале 2026?

**Эталон:** Чистая прибыль Wells Fargo в 3 кв. 2026 — $6.0 млрд.

**Ответ:** Чистая прибыль Wells Fargo в третьем квартале 2026 года — около $5.95 млрд [S1].

<details><summary>Источник 1: WFC_earnings_2026-10-13#0 · Exhibit 99.1</summary>

```
News Release | October 13, 2026 Wells Fargo Reports Third Quarter 2026 Net Income of $6.0 billion, or $1.87 per Diluted Share

| Company-wide Financial Summary | | |
| --- | --- | --- |
| Quarter ended | | |
| Sep 30, 2026 | Sep 30, 2025 | |
| Selected Income Statement Data ($ in millions except per share amounts) | | |
| Total revenue | $21,870 | 21,436 |
| Noninterest expense | 13,743 | 13,846 |
| Provision for credit losses 1 | 1,029 | 681 |
| Net income | 5,951 | 5,589 |
| Diluted earnings per common share | 1.87 | 1.66 |
| Selected Balance Sheet Data ($ in billions) | | |
| Average loans | $1,033.4 | 928.7 |
| Average deposits | 1,482.9 | 1,339.9 |
| CET1 2 | 10.0% | 11.0 |
| Performance Metrics | | |
| ROE 3 | 13.8% | 12.8 |
| ROTCE 4 | 16.3 | 15.2 |
```

</details>

## l08 — r11 (fact)

**Вопрос:** Во сколько NVIDIA обошлись американские ограничения на экспорт в Китай?

**Эталон:** NVIDIA списала $4.5 млрд в 1 кв. 2026 фин. года из-за требования лицензии на экспорт H20 в Китай.

**Ответ:** В результате требований правительства США NVIDIA понесла убыток в размере $4,5 миллиарда в первом квартале финансового года 2026, связанный с избыточными запасами и обязательствами по закупкам, так как спрос на продукты H20 уменьшился [S3].

<details><summary>Источник 1: NVDA_annual_2026-01-25#34 · Item 1. Business > Government Regulations</summary>

```
In April 2025, the USG informed us that it requires a license for export to China (including Hong Kong and Macau) and D:5 countries, or to companies headquartered or with an ultimate parent therein, of our H20 integrated circuits and any other circuits achieving the H20’s memory bandwidth, interconnect bandwidth, or combination thereof. As a result of these requirements, we incurred a $4.5 billion charge in the first quarter of fiscal year 2026 associated with H20 for excess inventory and purchase obligations, as the demand for H20 products diminished.

In August 2025, the USG granted licenses that would allow us to ship certain H20 products to certain China-based customers. We generated approximately $60 million in H20 revenue under those licenses. USG officials expressed an expectation that the USG will receive 15% or more of the revenue generated from licensed sales of our products, but the USG did not publish a regulation codifying such requirement.

In February 2026, the USG granted a license that would allow us to ship small amounts of H200 products to specific China-based customers. To date, we have not generated any revenue under the H200 licensing program, and do not yet know whether any imports will be allowed into China. The license requires that the H200s go through an inspection process in the United States prior to any shipment to the customer. As a result, any H200 shipped under the new licensing program will be subject to a 25% tariff upon importation into the United States.

In the event that we are able to sell licensed products into the China market, we may not be able to pass along all or any of the tariff to our customers, and may be subject to litigation, increased costs, and a harmed competitive position.
```

</details>

## l09 — r27 (no_answer)

**Вопрос:** Какая выручка у JPMorgan в четвёртом квартале 2026 года?

**Эталон:** В документах этого нет: последний отчёт JPMorgan в корпусе — за 3 кв. 2026.

**Ответ:** Выручка JPMorgan в четвёртом квартале 2026 года составила $50.2 billion [S1].

<details><summary>Источник 1: JPM_earnings_2026-10-13#3 · THIRD-QUARTER 2026 RESULTS 1</summary>

```
| Firmwide Metrics | n | Reported revenue of $50.2 billion and managed revenue 2 of $50.9 billion |
| --- | --- | --- |
| n | Average loans up 20% YoY and 6% QoQ; average deposits up 5% YoY, down 3% QoQ | |
```

</details>

## l10 — r16 (narrative)

**Вопрос:** Что в отчете Tesla о Киберкаб за третий квартал 2026 года?

**Эталон:** С 3 сентября 2026 Tesla начала возить пассажиров Robotaxi на Cybercab в Остине; Cybercab добавлен во флот Robotaxi.

**Ответ:** В третьем квартале 2026 года Tesla начала предоставлять поездки на Robotaxi с использованием Киберкабов в Остине. Мы достигли почти двух миллионов накопленных несупервизируемых миль для нашего Robotaxi-сервиса на конец квартала [S4].

<details><summary>Источник 1: TSLA_earnings_2026-10-21#10 · </summary>

```
We also deployed the first pre-assembled Megacharger to support the Tesla Semi ramp. 7 Tesla SI Training Capacity Ramp (MW of Compute) 0 50 100 150 200 250 300 350 400 450 Existing Capacity Future Planned Capacity (1) Excludes 40 MW of other compute not part of Cortex 1 or Cortex 2.

S I & O T H E R S E R V I C E S Cumulative Unsupervised Robotaxi Miles Cumulative Miles Driven with FSD (Supervised)1 (billions) 8 (1) Active driver supervision required; does not make the vehicle autonomous. FSD (Supervised)1 FSD adoption continued to increase during the quarter, including record net new new deliveries including FSD subscriptions. To date, we have received four additional FSD approvals since the end of Q2 (Croatia, Slovenia, Czech Republic and Slovakia) with FSD now available in a total of nine EU countries and used by over 100,000 customers logging more than 160 million kilometers since initial approval. Robotaxi We began deployment of Cybercab into our Robotaxi fleet in Austin. We reached nearly two million cumulative unsupervised miles for our Robotaxi service as of the end of the quarter. Operating hours in Austin are now 6am to midnight, and we expect to reduce wait times via increased fleet supply and improvement of Robotaxi orchestration algorithms. Grok is available in Cybercab with access to Grok Bot and Connectors, which allows users to manage their inbox, calendars, files, chats and tasks – all hands free via voice command – making Cybercab a mode of transport, a productivity space and, with our entertainment options, a second living room.
```

</details>

## l11 — r26 (narrative)

**Вопрос:** Платит ли Tesla дивиденды?

**Эталон:** Нет: Tesla никогда не объявляла и не платила денежные дивиденды и не планирует в обозримом будущем.

**Ответ:** Да, Tesla выплачивает ежеквартальные дивиденды по обыкновенным акциям [S1].

<details><summary>Источник 1: TSLA_annual_2025-12-31#104 · ITEM 5. MARKET FOR REGISTRANT’S COMMON EQUITY, RELATED STOCKHOLDER MATTERS AND ISSUER PURCHASES OF EQUITY SECURITIES > Stock Performance Graph</summary>

```
This performance graph shall not be deemed “filed” for purposes of Section 18 of the Securities Exchange Act of 1934, as amended (the “Exchange Act”), or incorporated by reference into any filing of Tesla, Inc. under the Securities Act of 1933, as amended (the “Securities Act”), or the Exchange Act, except as shall be expressly set forth by specific reference in such filing.

The following graph shows a comparison, from January 1, 2021 through December 31, 2025, of the cumulative total return on our common stock, The NASDAQ Composite Index and a group of all public companies sharing the same SIC code as us, which is SIC code 3711, “Motor Vehicles and Passenger Car Bodies” (Motor Vehicles and Passenger Car Bodies Public Company Group). Such returns are based on historical results and are not intended to suggest future performance. Data for The NASDAQ Composite Index and the Motor Vehicles and Passenger Car Bodies Public Company Group assumes an investment of $100 on January 1, 2021 and reinvestment of dividends. We have never declared or paid cash dividends on our common stock nor do we anticipate paying any such cash dividends in the foreseeable future.
```

</details>

## l12 — r27 (no_answer)

**Вопрос:** Какая выручка у JPMorgan в четвёртом квартале 2026 года?

**Эталон:** В документах этого нет: последний отчёт JPMorgan в корпусе — за 3 кв. 2026.

**Ответ:** В документах этого нет.

_Источников нет: бот ответил «не знаю»._

## l13 — r09 (fact)

**Вопрос:** Какие были выручка и прибыль на акцию у Texas Instruments в третьем квартале 2026?

**Эталон:** Texas Instruments в 3 кв. 2026: выручка $6.06 млрд, прибыль на акцию $2.62 (чистая прибыль $2.43 млрд).

**Ответ:** Выручка составила $6,055 миллиарда [S3]. Прибыль на акцию составила $2.62 [S2].

<details><summary>Источник 1: TXN_earnings_2026-10-21#4 · TEXAS INSTRUMENTS INCORPORATED AND SUBSIDIARIES</summary>

```
| Consolidated Statements of Income | For Three Months Ended September 30, | |
| --- | --- | --- |
| (In millions, except per-share amounts) | 2026 | 2025 |
| Revenue | $6,055 | $4,742 |
| Cost of revenue (COR) | 2,168 | 2,019 |
| Gross profit | 3,887 | 2,723 |
| Research and development (R&D) | 530 | 518 |
| Selling, general and administrative (SG&A) | 476 | 457 |
| Acquisition charges | 7 | — |
| Restructuring charges/other | — | 85 |
| Operating profit | 2,874 | 1,663 |
| Other income (expense), net (OI&E) | 72 | 62 |
| Interest and debt expense | 141 | 141 |
| Income before income taxes | 2,805 | 1,584 |
| Provision for income taxes | 380 | 220 |
| Net income | $2,425 | $1,364 |
| Diluted earnings per common share | $2.62 | $1.48 |
| Average shares outstanding: | | |
| Basic | 914 | 909 |
| Diluted | 921 | 914 |
| Cash dividends declared per common share | $1.42 | $1.36 |
| Supplemental Information (Quarterly, except as noted) | | |
| Provision for income taxes is based on the following: | | |
| Operating taxes (calculated using the estimated annual effective tax rate) | $390 | $249 |
| Discrete tax items | (10) | (29) |
| Provision for income taxes (effective taxes) | $380 | $220 |
```

</details>

<details><summary>Источник 2: TXN_earnings_2026-10-21#5 · TEXAS INSTRUMENTS INCORPORATED AND SUBSIDIARIES</summary>

```
| Consolidated Statements of Income | For Three Months Ended September 30, | |
| --- | --- | --- |
| A portion of net income is allocated to unvested restricted stock units (RSUs) on which we pay dividend equivalents. Diluted EPS is calculated using the following: | | |
| Net income | $2,425 | $1,364 |
| Income allocated to RSUs | (14) | (8) |
| Income allocated to common stock for diluted EPS | $2,411 | $1,356 |
```

</details>

## l14 — r05 (similar_docs)

**Вопрос:** Третий квартал 2026 года какая чистая прибыль у читигруп по их отчету?

**Эталон:** Чистая прибыль Citigroup в 3 кв. 2026 — $5.2 млрд.

**Ответ:** Чистая прибыль Citigroup составила $5.2 миллиарда в третьем квартале 2026 года, по сравнению с $3.8 миллиарда в аналогичном периоде прошлого года [S1].

<details><summary>Источник 1: C_earnings_2026-10-13#7 · Citigroup</summary>

```
Citigroup net income was $5.2 billion in the third quarter 2026, compared to net income of $3.8 billion in the prior-year period on a reported basis, driven by higher revenues and lower expenses, partially offset by a higher provision for credit losses. Excluding the notable item, net income in the prior-year period was $4.5 billion (3) . Citigroup’s effective tax rate was approximately 26% in the third quarter 2026 compared to 29% in the third quarter 2025.

Citigroup’s total allowance for credit losses was $22.4 billion at quarter end, compared to $23.8 billion at the end of the prior-year period. Total ACL on loans was $20.1 billion at quarter end, compared to $19.2 billion at the end of the prior-year period, with a reserve-to-funded loan ratio of 2.5%, down from 2.7% in the prior-year period. Total non-accrual loans decreased $0.4 billion, or 12%, from the prior-year period to $3.3 billion. Corporate non-accrual loans decreased $0.3 billion, or 16%, from the prior-year period to $1.7 billion, driven by upgrades and repayments in Markets , partially offset by idiosyncratic downgrades in Services . Consumer non-accrual loans decreased $0.1 billion, or 5%, from the prior-year period to $1.5 billion, driven by Wealth , partially offset by Legacy Franchises, in All Other .
```

</details>

## l15 — r22 (version_trap)

**Вопрос:** Какая валовая маржа была у TSMC во втором квартале 2026 года?

**Эталон:** Валовая маржа TSMC во 2 кв. 2026 — 67.7%.

**Ответ:** Валовая маржа TSMC во втором квартале 2026 года составила 67.7%; рост связан с ослаблением тайваньского доллара [S1].

<details><summary>Источник 1: TSM_management_report_2026Q2#1 · Financial Highlights</summary>

```
Second Quarter 2026

- Net revenue was NT$1,270.38 billion, representing a 12.0% increase from NT$1,134.10 billion in 1Q26 and a 36.0% increase from NT$933.79 billion in 2Q25.

- Gross margin was 67.7%, 1.5 percentage points higher than 1Q26 and 9.1 percentage points higher than 2Q25.

- Operating margin was 60.3%, up 2.2 percentage points from 1Q26 and up 10.7 percentage points from 2Q25.

- Non-operating items were a gain of NT$ 95.83 billion, compared to a gain of NT$28.83 billion in 1Q26 and a gain of NT$ 29.61 billion in 2Q25. The increase was mainly due to disposal and mark-to-market gains of NT$63.20 billion on Vanguard International Semiconductor Corp. (VIS) shares.

- Net income attributable to shareholders of the parent company was NT$706.56 billion, up 23.4% from 1Q26 and up 77.4% from 2Q25. Net profit margin was 55.6% and diluted EPS was NT$27.25.
```

</details>

## l16 — r05 (similar_docs)

**Вопрос:** Третий квартал 2026 года какая чистая прибыль у читигруп по их отчету?

**Эталон:** Чистая прибыль Citigroup в 3 кв. 2026 — $5.2 млрд.

**Ответ:** В документах этого нет.

_Источников нет: бот ответил «не знаю»._

## l17 — r12 (version_trap)

**Вопрос:** Какая грос маргин TSMC в третьем квартале 2026 года?

**Эталон:** Валовая маржа TSMC в 3 кв. 2026 — 66.4%.

**Ответ:** Гросс маржин составила 66.4% в третьем квартале 2026 года, что на 1.3 процентных пункта ниже, чем во втором квартале 2026 года и на 6.9 процентных пункта выше, чем в третьем квартале 2025 года [S1].

<details><summary>Источник 1: TSM_management_report_2026Q3#1 · Financial Highlights</summary>

```
Third Quarter 2026

- Net revenue was NT$1,494.24 billion, representing a 17.6% increase from NT$1,270.38 billion in 2Q26 and a 50.9% increase from NT$989.92 billion in 3Q25.

- Gross margin was 66.4%, 1.3 percentage points lower than 2Q26 and 6.9 percentage points higher than 3Q25.

- Operating margin was 58.7%, down 1.6 percentage points from 2Q26 and up 8.1 percentage points from 3Q25.

- Non-operating items were a gain of NT$ 34.59 billion, compared to a gain of NT$95.83 billion in 2Q26 and a gain of NT$24.68 billion in 3Q25.

- Net income attributable to shareholders of the parent company was NT$763.06 billion, up 8.0% from 2Q26 and up 68.7% from 3Q25. Net profit margin was 51.1% and diluted EPS was NT$29.43.
```

</details>

## l18 — r07 (fact)

**Вопрос:** На сколько выросли продажи AWS по сравнению с прошлым годом в третьем квартале 26го?

**Эталон:** Продажи AWS в 3 кв. 2026 выросли на 39% год к году, до $46.0 млрд.

**Ответ:** Продажи AWS выросли на 39% год к году, до $46.0 billion, а операционная маржа AWS составила 40% [S1].

<details><summary>Источник 1: AMZN_earnings_2026-10-29#0 · AMAZON.COM ANNOUNCES THIRD QUARTER RESULTS</summary>

```
Operating income was $28.1 billion and operating margin was 13.9%—Amazon’s highest operating margin ever

AWS net sales increased 39.3%—its fastest growth in nearly five years—to a $184 billion annualized revenue run rate

SEATTLE—(BUSINESS WIRE) October 29, 2026—Amazon.com, Inc. (NASDAQ: AMZN) today announced financial results for its third quarter ended September 30, 2026.

• Net sales increased 12% to $201.9 billion in the third quarter, compared with $180.2 billion in third quarter 2025. Excluding the $0.9 billion unfavorable impact from year-over-year changes in foreign exchange rates throughout the quarter, net sales increased 13% compared with third quarter 2025. As a reminder, Prime Day timing shifted this year, with the event occurring in Q2 for most large countries. In 2025, Prime Day occurred entirely in Q3. Excluding this shift, third quarter year-over-year growth would have been approximately 400 basis points higher.

• North America segment sales increased 6% year-over-year to $112.9 billion.

• International segment sales increased 5% year-over-year to $43.1 billion, or increased 8% excluding changes in foreign exchange rates.

• AWS segment sales increased 39% year-over-year to $46.0 billion.

• Operating income increased to $28.1 billion in the third quarter, compared with $17.4 billion in third quarter 2025.

• North America segment operating income was $8.7 billion, compared with $4.8 billion in third quarter 2025.

• International segment operating income was $1.6 billion, compared with $1.2 billion in third quarter 2025.

• AWS segment operating income was $17.8 billion, compared with $11.4 billion in third quarter 2025.
```

</details>
