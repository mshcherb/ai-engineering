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
make run ARGS="--run gpt4o_mini_t0 --limit 10"
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
config.yaml           моделі, temperature / top_p, timeout, retries
prompts/              версії промптів + CHANGELOG.md
data/texts.jsonl      49 знеособлених текстів (Telegram + Reddit)
results/              виходи моделей
scripts/              збірка датасету, перевірка середовища
```

## Схема

Одна картка на текст:

| поле | тип |
|---|---|
| `language` | enum: uk / ru / en / mixed |
| `is_about_stocks` | bool |
| `mentions[]` | список згадок, кожна: `company`, `ticker`, `asset_type` (enum), `sentiment` (enum), `reasoning`, `price_target`, `horizon` (enum), `quote` |
| `summary` | одне речення |

Автор, дата і джерело не запитуються в моделі — вони беруться з даних.

## Дані

- **Telegram:** 2 інвестиційні канали за 11–20.10.2026 (експорт Telegram Desktop).
- **Reddit:** r/stocks та r/investing, top за тиждень 13–20.10.2026.

Сирі експорти з нікнеймами в репозиторій не потрапляють. `scripts/build_dataset.py` відбирає різноманітні тексти (з тикерами, компанії словами, ринок без компаній, шум; короткі / середні / довгі) і знеособлює їх: посилання → `<URL>`, `@нік` / `u/нік` → `<USER>`, повідомлення з іменами виключені.

## Кожен запис результату

`id`, `model`, `provider`, `prompt_version`, `temperature`, `top_p`, `status` (ok / invalid / error), `latency_s`, `attempts`, `tokens_in`, `tokens_out`, `cost_usd`, `output` (картка), `error`, `raw` (сирий вихід, якщо невалідний).
