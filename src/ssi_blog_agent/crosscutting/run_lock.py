"""Run-lock (Chunk 6): a Redis flag so an overlapping cron + manual run can't
double-publish or double-spend. SET NX with a safety TTL; released in a
finally. If Redis is unavailable the lock is skipped (fail-open — better to run
than to never run a weekly job)."""

import datetime

import httpx

from ssi_blog_agent.config import settings

LOCK_KEY = "ssi:run_lock"
LOCK_TTL_SECONDS = 3 * 3600  # safety expiry so a crashed run can't wedge forever


def _command(command: list) -> dict | None:
    if not settings.upstash_redis_url or not settings.upstash_redis_token:
        return None
    resp = httpx.post(
        settings.upstash_redis_url,
        headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
        json=command,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def acquire() -> bool:
    """True if the lock was acquired (or Redis is unavailable -> fail-open)."""
    try:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        res = _command(["SET", LOCK_KEY, now, "NX", "EX", str(LOCK_TTL_SECONDS)])
        if res is None:
            return True  # no Redis configured -> don't block the run
        return res.get("result") == "OK"
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] run-lock acquire failed (continuing): {exc}")
        return True


def release() -> None:
    try:
        _command(["DEL", LOCK_KEY])
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] run-lock release failed: {exc}")
