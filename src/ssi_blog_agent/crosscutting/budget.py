"""Cost circuit breaker (Chunk 6).

Reads the running DeepSeek usage log and estimates spend; the run halts
research gracefully if it crosses the per-run cap. Prices are configurable
placeholders — set real DeepSeek rates via env to make the euro figure exact;
the *mechanism* (halt + degrade to a partial report) is what matters.
"""

import os

from ssi_blog_agent.config import settings

# €/1K tokens. Override with real DeepSeek pricing via env when known.
PRICE_PER_1K_INPUT_EUR = {
    "deepseek-v4-flash": float(os.getenv("PRICE_FLASH_IN", "0.0002")),
    "deepseek-v4-pro": float(os.getenv("PRICE_PRO_IN", "0.0025")),
}
PRICE_PER_1K_OUTPUT_EUR = {
    "deepseek-v4-flash": float(os.getenv("PRICE_FLASH_OUT", "0.0004")),
    "deepseek-v4-pro": float(os.getenv("PRICE_PRO_OUT", "0.0050")),
}


def estimate_cost_eur(usage_log: list[dict]) -> float:
    total = 0.0
    for u in usage_log:
        model = u["model"]
        total += u["input_tokens"] / 1000 * PRICE_PER_1K_INPUT_EUR.get(model, 0.001)
        total += u["output_tokens"] / 1000 * PRICE_PER_1K_OUTPUT_EUR.get(model, 0.002)
    return total


def exceeded(usage_log: list[dict]) -> bool:
    return estimate_cost_eur(usage_log) > settings.max_run_cost_eur
