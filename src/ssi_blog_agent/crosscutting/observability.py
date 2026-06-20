"""Kevyt webhook-ilmoitus ajon lopussa (Slack/email)."""

import httpx

from ssi_blog_agent.config import settings
from ssi_blog_agent.state import GraphState

STATUS_EMOJI = {
    "success": "✅",
    "partial": "⚠️",
    "failed": "❌",
    "skipped_locked": "⏸️",
}


def notify_run_result(state: GraphState) -> GraphState:
    status = state.get("run_status", "failed")
    emoji = STATUS_EMOJI.get(status, "❓")

    if status == "success":
        text = f"{emoji} Raportti julkaistu onnistuneesti"
    elif status == "partial":
        failed_agents = [
            r.agent_name for r in state.get("agent_results", []) if r.status == "failed"
        ]
        text = f"{emoji} Raportti julkaistu osittaisilla tiedoilla (epäonnistuneet: {failed_agents})"
    elif status == "skipped_locked":
        text = f"{emoji} Ajo ohitettu: edellinen ajo on yhä kesken (run-lukko)"
    else:
        text = f"{emoji} Ajo epäonnistui kokonaan"

    if settings.slack_webhook_url:
        try:
            httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
        except httpx.HTTPError:
            pass  # ei kaadeta ajoa hälytyksen epäonnistumisesta

    return state
