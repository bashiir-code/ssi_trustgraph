import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    upstash_redis_url: str = os.getenv("UPSTASH_REDIS_REST_URL", "")
    upstash_redis_token: str = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")

    max_run_cost_eur: float = float(os.getenv("MAX_RUN_COST_EUR", "1.50"))
    monthly_budget_eur: float = float(os.getenv("MONTHLY_BUDGET_EUR", "5.00"))

    cache_freshness_days: int = 7
    triage_max_retries: int = 2
    research_concurrency: int = int(os.getenv("RESEARCH_CONCURRENCY", "3"))


settings = Settings()
