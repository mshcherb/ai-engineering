"""One client for every OpenAI-compatible provider (OpenRouter, Ollama).

Only base_url, api key and model name differ between providers.
Adds a per-request timeout and retries with exponential backoff.
"""
import os
import time
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from extractor.schema import json_schema

# Transient errors worth retrying; anything else (e.g. 400 bad request) fails at once
RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)


@dataclass
class CallResult:
    content: str | None = None
    error: str | None = None
    latency_s: float = 0.0
    attempts: int = 0
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


class LLMClient:
    def __init__(self, provider: str, provider_cfg: dict, model: str,
                 timeout_s: float, max_retries: int, backoff_base_s: float):
        self.provider = provider
        self.model = model
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        base_url = os.getenv(provider_cfg.get("base_url_env", ""), provider_cfg["base_url"])
        api_key = (os.getenv(provider_cfg["api_key_env"])
                   if "api_key_env" in provider_cfg else provider_cfg.get("api_key"))
        if not api_key:
            raise RuntimeError(f"{provider}: API key missing, set {provider_cfg.get('api_key_env')} in .env")
        # max_retries=0: the SDK must not retry on its own, retries are handled below
        self.client = OpenAI(base_url=base_url, api_key=api_key,
                             timeout=timeout_s, max_retries=0)

    def extract(self, system_prompt: str, text: str,
                temperature: float, top_p: float) -> CallResult:
        result = CallResult()
        extra = {"usage": {"include": True}} if self.provider == "openrouter" else None
        start = time.perf_counter()
        for attempt in range(1, self.max_retries + 2):
            result.attempts = attempt
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    temperature=temperature,
                    top_p=top_p,
                    response_format={"type": "json_schema", "json_schema": json_schema()},
                    extra_body=extra,
                )
            except RETRYABLE as e:
                result.error = f"{type(e).__name__}: {e}"
                if attempt > self.max_retries:
                    break
                time.sleep(self.backoff_base_s * 2 ** (attempt - 1))
                continue
            except Exception as e:
                result.error = f"{type(e).__name__}: {e}"
                break

            result.error = None
            result.content = r.choices[0].message.content
            if r.usage:
                result.tokens_in = r.usage.prompt_tokens
                result.tokens_out = r.usage.completion_tokens
                result.cost_usd = (r.usage.model_extra or {}).get("cost")
            break
        result.latency_s = round(time.perf_counter() - start, 3)
        return result
