"""Token-pohjainen kustannuslaskuri ja budjettikatkaisija (Cost Circuit Breaker)."""

from ssi_blog_agent.config import settings

# Karkea €/1K-token -hinnasto DeepSeek-malleille. TODO: päivitä todellisten
# hintojen mukaan ja lue tarkka käyttö API-vastauksen usage-kentästä.
PRICE_PER_1K_TOKENS_EUR = {
    "deepseek-v4-flash": 0.0003,
    "deepseek-v4-pro": 0.003,
}


class BudgetTracker:
    def __init__(self) -> None:
        self.spent_eur: float = 0.0

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        price = PRICE_PER_1K_TOKENS_EUR.get(model, 0.001)
        self.spent_eur += (input_tokens + output_tokens) / 1000 * price

    def exceeded(self) -> bool:
        return self.spent_eur > settings.max_run_cost_eur


budget_tracker = BudgetTracker()
