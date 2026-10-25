# Stock Opinion Extractor

Курсовий проєкт AI Engineering (robot_dreams, 2 потік).

Сервіс витягує структуровані дані з «брудних» текстів інвесторських чатів і форумів (Telegram, Reddit): які компанії згадуються, яке ставлення автора (bullish / bearish / neutral / mixed), аргумент, цільова ціна, горизонт і цитата-доказ. Порівнює провайдерську модель (OpenRouter) з локальною (Ollama).

Кейс 1 — **Structured Extraction Service**.

## Запуск

Потрібно: Docker + Docker Compose, `make`, ключ [OpenRouter](https://openrouter.ai/).

```bash
cp .env.example .env        # вписати OPENROUTER_API_KEY
make run                    # підняти контейнери і прогнати всі тексти
```

Результат — файл `results/<час>_<конфіг>_<версія промпту>.jsonl`.

Інші команди:

```bash
make run-sample             # швидка перевірка на 3 текстах
make run ARGS="--run llama32_3b_t0 --prompt v2 --limit 10"
make eval                   # оцінити останні прогони на golden set -> results/metrics.md
make compare                # прогнати всі конфіги і оцінити (локальна модель ~1 год на конфіг)
make check                  # перевірити, що OpenRouter і Ollama відповідають
make down
```

Локальна модель для кроку 2 (один раз):

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

## Структура

```
extractor/schema.py   схема PostCard (Pydantic), з неї генерується JSON Schema
extractor/client.py   один клієнт для OpenRouter і Ollama: structured output, timeout, retry
extractor/run.py      прогін датасету, валідація, логування результатів
extractor/evaluate.py метрики проти golden set: точність по полях, % валідних, latency, вартість
config.yaml           моделі, temperature / top_p, timeout, retries
prompts/              версії промптів + CHANGELOG.md
data/texts.jsonl      49 знеособлених текстів (Telegram + Reddit)
data/golden.json      15 текстів, розмічених вручну (правила — data/LABELING.md)
results/              виходи моделей
scripts/              збірка датасету, перевірка середовища
```

## Схема

Одна картка на текст:

| поле | тип |
|---|---|
| `language` | enum: uk / ru / en / mixed / unknown |
| `is_about_stocks` | bool |
| `mentions[]` | список згадок, кожна: `company`, `ticker`, `asset_type` (enum), `sentiment` (enum), `reasoning`, `price_target`, `horizon` (enum), `quote` |
| `summary` | одне речення |

Автор, дата і джерело не запитуються в моделі — вони беруться з даних.

## Дані

- **Telegram:** 2 інвестиційні канали за 11–20.10.2026 (експорт Telegram Desktop).
- **Reddit:** r/stocks та r/investing, top за тиждень 13–20.10.2026.

Сирі експорти з нікнеймами в репозиторій не потрапляють. `scripts/build_dataset.py` відбирає різноманітні тексти (з тикерами, компанії словами, ринок без компаній, шум; короткі / середні / довгі) і знеособлює їх: посилання → `<URL>`, `@нік` / `u/нік` → `<USER>`, повідомлення з іменами виключені.

## Моделі та конфігурації

| конфіг | модель | temperature / top_p |
|---|---|---|
| `gpt4o_mini_t0` | `openai/gpt-4o-mini` (OpenRouter) | 0.0 / 1.0 |
| `gpt4o_mini_t07` | `openai/gpt-4o-mini` (OpenRouter) | 0.7 / 0.9 |
| `llama32_3b_t0` | `llama3.2:3b` (Ollama, CPU) | 0.0 / 1.0 |
| `llama32_3b_t07` | `llama3.2:3b` (Ollama, CPU) | 0.7 / 0.9 |

Обидві моделі йдуть через один `LLMClient` — різняться лише `base_url`, ключ і назва моделі. Для Ollama таймаут 300 с (CPU, ~10 токенів/с).

## Метрики (`make eval`)

- **% valid** — частка відповідей, що пройшли схему; **latency p50 / p95**; **$ / 1000 документів** (з `usage.cost` OpenRouter; локальна модель — $0 за API).
- **Точність на golden set:** `is_about_stocks`, `language`; для згадок — precision / recall / F1 (зіставлення за тикером або назвою); для зіставлених згадок — `sentiment`, `asset_type`, `horizon`, `price_target`.
- Невалідна відповідь рахується як помилка в усіх полях.
- `results/errors.md` — кожна розбіжність з golden set (матеріал для аналізу помилок).

## Кожен запис результату

`id`, `model`, `provider`, `prompt_version`, `temperature`, `top_p`, `status`, `latency_s`, `attempts`, `tokens_in`, `tokens_out`, `cost_usd`, `output` (картка), `error`, `repair_reason`, `raw` (сирий вихід, якщо невалідний).

Статуси:
- `ok` — валідна картка з першої спроби;
- `repaired` — перша відповідь не пройшла валідацію, модель отримала список помилок і виправила (одна спроба);
- `failed` — невалідна й після виправлення;
- `error` — відповіді немає (мережа, таймаут, `deadline_s`).

Валідація = JSON Schema (structured output) + перевірки, яких схема не виражає (формат тикера: `NVDA`, `BRK.B` або `null`, а не рядок `"null"` чи `$tsla`).

## Промпти

`prompts/v1.md`, `prompts/v2.md` — версія й дата у front matter, що й чому змінено — у `prompts/CHANGELOG.md`. Версія за замовчуванням — `prompt_version` у `config.yaml`, інша — `--prompt v2`.
