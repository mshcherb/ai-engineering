"""One client for every OpenAI-compatible provider (OpenRouter, Ollama).

Only base_url, api key and model name differ between providers.
Adds a per-request timeout, a hard deadline per call and retries with exponential backoff.

The response is streamed: the httpx timeout only limits the gap between bytes,
so a generation that keeps going (or a stuck server) is cut by the deadline instead.
"""
import os
import time
from dataclasses import dataclass

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from extractor.schema import json_schema

# Transient errors worth retrying; anything else (e.g. 400 bad request) fails at once
RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError,
             httpx.TimeoutException)


class DeadlineExceeded(Exception):
    """The call took longer than deadline_s; not retried, the text is marked as error."""


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
                 timeout_s: float, max_retries: int, backoff_base_s: float,
                 max_tokens: int | None = None, deadline_s: float = 120):
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.deadline_s = provider_cfg.get("deadline_s", deadline_s)
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        base_url = os.getenv(provider_cfg.get("base_url_env", ""), provider_cfg["base_url"])
        api_key = (os.getenv(provider_cfg["api_key_env"])
                   if "api_key_env" in provider_cfg else provider_cfg.get("api_key"))
        if not api_key:
            raise RuntimeError(f"{provider}: API key missing, set {provider_cfg.get('api_key_env')} in .env")
        # max_retries=0: the SDK must not retry on its own, retries are handled below
        # a provider may override the timeout (a local model on CPU is much slower)
        self.client = OpenAI(base_url=base_url, api_key=api_key,
                             timeout=provider_cfg.get("timeout_s", timeout_s), max_retries=0)

    def extract(self, system_prompt: str, text: str,
                temperature: float, top_p: float) -> CallResult:
        result = CallResult()
        extra = {"usage": {"include": True}} if self.provider == "openrouter" else None
        start = time.perf_counter()
        for attempt in range(1, self.max_retries + 2):
            result.attempts = attempt
            try:
                content, usage = self._call(system_prompt, text, temperature, top_p, extra)
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
            result.content = content
            if usage:
                result.tokens_in = usage.prompt_tokens
                result.tokens_out = usage.completion_tokens
                result.cost_usd = (usage.model_extra or {}).get("cost")
            break
        result.latency_s = round(time.perf_counter() - start, 3)
        return result

    def _call(self, system_prompt: str, text: str, temperature: float, top_p: float,
              extra: dict | None):
        """One streamed request. Returns (content, usage)."""
        start = time.perf_counter()
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=self.max_tokens,
            response_format={"type": "json_schema", "json_schema": json_schema()},
            stream=True,
            stream_options={"include_usage": True},  # usage arrives in the last chunk
            extra_body=extra,
        )
        parts, usage = [], None
        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    parts.append(chunk.choices[0].delta.content)
                if chunk.usage:
                    usage = chunk.usage
                if time.perf_counter() - start > self.deadline_s:
                    raise DeadlineExceeded(f"no complete answer after {self.deadline_s}s")
        finally:
            stream.close()  # closing the connection makes Ollama stop generating
        return "".join(parts) or None, usage
