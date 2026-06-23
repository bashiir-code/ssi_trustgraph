"""Run-result notification (Chunk 6): a Slack webhook at the end of every run.

Serverless + weekly -> without an alert a broken pipeline could go unnoticed
for weeks. Never raises (a failed notification must not fail the run).
"""

import httpx

from ssi_blog_agent.config import settings

_EMOJI = {
    "success": "✅",
    "partial": "⚠️",
    "failed": "❌",
    "skipped_locked": "⏸️",
}


def notify(status: str, detail: str = "") -> None:
    emoji = _EMOJI.get(status, "❓")
    text = {
        "success": f"{emoji} Viikkoraportti julkaistu onnistuneesti.",
        "partial": f"{emoji} Viikkoraportti julkaistu OSITTAISILLA tiedoilla.",
        "failed": f"{emoji} Ajo epäonnistui.",
        "skipped_locked": f"{emoji} Ajo ohitettu — edellinen ajo on yhä kesken (run-lukko).",
    }.get(status, f"{emoji} {status}")
    if detail:
        text += f"\n{detail}"

    if not settings.slack_webhook_url:
        print(f"[notify] {text}")
        return
    try:
        httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
    except httpx.HTTPError as exc:
        print(f"  [warn] slack notify failed: {exc}")
