.PHONY: up run run-sample eval compare data check down corpus ingest index eval-retrieval ask answers-sample lint-testset eval-answers eval-ci calibrate

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

# HW2: embed chunks (cached in data/corpus/embeddings.npz; first run ~25 min on CPU)
index: up
	docker compose exec python python -m rag.index
	docker compose exec python python -m rag.index --chunks fixed

# HW2: recall@k / MRR for vector, BM25, hybrid, hybrid+rerank on both chunkings
eval-retrieval: up
	docker compose exec python python -m evals.retrieval_eval

# HW2: answer one question with sources: make ask Q="Какая грос маргин TSMC в третьем квартале 2026 года?"
ask: up
	docker compose exec python python -m rag.answer "$(Q)"

# HW2: all retrieval questions through the RAG pipeline -> evals/results/answers_sample_<prompt>.md
answers-sample: up
	docker compose exec python python -m rag.answer --sample

# HW2: check evals/testset.jsonl against the corpus (doc ids, evidence, must facts)
lint-testset: up
	docker compose exec python python -m evals.testset

# HW2: testset through RAG -> evals/results/answers.{jsonl,json,md}; ARGS=--rescore scores saved answers for free
eval-answers: up
	docker compose exec python python -m evals.answer_eval $(ARGS)

# HW2: what CI runs (.github/workflows/evals.yml): answers + LLM judge + the gate from evals/baseline.json
eval-ci: up
	docker compose exec python python -m evals.testset
	docker compose exec python python -m evals.answer_eval --judge --gate

# HW2: judge vs hand labels (evals/labels.jsonl); ARGS="--run gpt4o_mini_t0 --grounded-prompt judge_grounded_v3"
calibrate: up
	docker compose exec python python -m evals.judge --calibrate $(ARGS)

down:
	docker compose down
