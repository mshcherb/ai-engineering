.PHONY: up run run-sample data check down

# Start containers (python + ollama)
up:
	docker compose up -d --build

# Run extraction over the whole dataset with the default config
run: up
	docker compose exec python python main.py $(ARGS)

# Quick smoke test on the first 3 texts
run-sample: up
	docker compose exec python python main.py --limit 3

# Rebuild data/texts.jsonl from raw exports (raw data is local only, see README)
data: up
	docker compose exec python python scripts/build_dataset.py

# Check that OpenRouter and Ollama answer
check: up
	docker compose exec python python scripts/check_env.py

down:
	docker compose down
