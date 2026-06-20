"""Real DeepSeek client (OpenAI-compatible chat completions).

Tracks cumulative token usage per process so Chunk 6's budget circuit
breaker can read it later. Verified against the live API on 2026-06-20
(models deepseek-v4-flash, deepseek-v4-pro).
"""

import json

import httpx

from ssi_blog_agent.config import settings

DEFAULT_MODEL = "deepseek-v4-flash"

# Process-wide usage accumulator (input_tokens, output_tokens) per model.
usage_log: list[dict] = []


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    response_format: dict | None = None,
    temperature: float = 0.3,
    timeout: float = 90.0,
) -> str:
    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if response_format is not None:
        payload["response_format"] = response_format

    resp = httpx.post(
        f"{settings.deepseek_base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

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
