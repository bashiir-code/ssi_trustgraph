"""Real DeepSeek client (OpenAI-compatible chat completions).

Tracks cumulative token usage per process so Chunk 6's budget circuit
breaker can read it later. Retries transient transport errors (dropped
connections, timeouts) and 429/5xx with exponential backoff — a single
dropped connection must not throw away a whole run's research.
"""

import json

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ssi_blog_agent.config import settings

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT = 120.0

# Process-wide usage accumulator (input_tokens, output_tokens) per model.
usage_log: list[dict] = []


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        # RemoteProtocolError, ReadTimeout, ConnectError, ReadError, ...
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception(_is_retryable),
)
def _post_chat(payload: dict, timeout: float) -> dict:
    resp = httpx.post(
        f"{settings.deepseek_base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    response_format: dict | None = None,
    temperature: float = 0.3,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if response_format is not None:
        payload["response_format"] = response_format

    data = _post_chat(payload, timeout)

    usage = data.get("usage", {})
    usage_log.append(
        {
            "model": model,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }
    )

    return data["choices"][0]["message"]["content"]


def chat_json(messages: list[dict], model: str = DEFAULT_MODEL, **kwargs) -> dict:
    """Chat call constrained to a JSON object response."""
    content = chat(
        messages, model=model, response_format={"type": "json_object"}, **kwargs
    )
    return json.loads(content)
