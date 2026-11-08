.PHONY: up run run-sample eval compare data check down corpus ingest

# Start containers (python + ollama)
up:
	docker compose up -d --build

# Run extraction over the whole dataset with the default config
run: up
	docker compose exec python python main.py $(ARGS)

# Quick smoke test on the first 3 texts
run-sample: up
	docker compose exec python python main.py --limit 3

# Score the latest result of every run against data/golden.json -> results/metrics.md
eval: up
	docker compose exec python python -m extractor.evaluate

# Run every config from config.yaml, then score them (local model on CPU: ~1 h per config)
RUNS = gpt4o_mini_t0 gpt4o_mini_t07 llama32_3b_t0 llama32_3b_t07
compare: up
	for r in $(RUNS); do docker compose exec python python main.py --run $$r || exit 1; done
	docker compose exec python python -m extractor.evaluate

# Rebuild data/texts.jsonl from raw exports (raw data is local only, see README)
data: up
	docker compose exec python python scripts/build_dataset.py

# Check that OpenRouter and Ollama answer
check: up
	docker compose exec python python scripts/check_env.py

# HW2: download the RAG corpus from SEC EDGAR (needs SEC_USER_AGENT in .env; IR PDFs are saved by hand)
corpus: up
	docker compose exec python python scripts/fetch_corpus.py

# HW2: raw documents -> data/corpus/chunks.jsonl (+ ingest_report.json)
ingest: up
	docker compose exec python python -m rag.ingest

down:
	docker compose down
