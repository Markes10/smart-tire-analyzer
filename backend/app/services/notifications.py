"""
Notification integrations for model promotion and high-risk inference alerts.

Supports SMTP email, Slack incoming webhooks, and generic HTTP webhooks.
All channels are optional and disabled when their env vars are unset.
"""

from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
from urllib import error, request

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Send operational alerts through configured channels."""

    def __init__(self) -> None:
        self.enabled = settings.NOTIFICATIONS_ENABLED

    def notify_model_promoted(self, *, model_version: str, registry_path: str) -> dict[str, Any]:
        subject = f"Smart Tire: model promoted — {model_version}"
        body = (
            f"A quarantined hybrid model was promoted to active runtime.\n\n"
            f"Model version: {model_version}\n"
            f"Registry: {registry_path}\n"
        )
        return self._dispatch(subject, body, event="model_promoted", extra={"model_version": model_version})

    def notify_high_risk_analysis(
        self,
        *,
        session_id: str,
        risk_level: str,
        health_score: float | None,
        avg_tread_mm: float | None,
    ) -> dict[str, Any]:
        subject = f"Smart Tire: {risk_level} risk analysis ({session_id[:8]})"
        body = (
            f"A tire analysis returned elevated risk.\n\n"
            f"Session: {session_id}\n"
            f"Risk level: {risk_level}\n"
            f"Health score: {health_score}\n"
            f"Average tread depth (mm): {avg_tread_mm}\n"
        )
        return self._dispatch(
            subject,
            body,
            event="high_risk_analysis",
            extra={
                "session_id": session_id,
                "risk_level": risk_level,
                "health_score": health_score,
                "avg_tread_mm": avg_tread_mm,
            },
        )

    def _dispatch(
        self,
        subject: str,
        body: str,
        *,
        event: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            logger.debug("Notifications disabled; skipping event=%s", event)
            return {"sent": False, "reason": "notifications_disabled", "event": event}

        results: dict[str, Any] = {"event": event, "channels": {}}
        payload = {"event": event, "subject": subject, "body": body, "extra": extra or {}}

        if settings.SMTP_HOST and settings.NOTIFICATION_EMAIL_TO:
            results["channels"]["email"] = self._send_email(subject, body)
        if settings.SLACK_WEBHOOK_URL:
            results["channels"]["slack"] = self._send_slack(subject, body, payload)
        if settings.NOTIFICATION_WEBHOOK_URL:
            results["channels"]["webhook"] = self._send_webhook(payload)

        sent = any(result.get("ok") for result in results["channels"].values())
        results["sent"] = sent
        if not results["channels"]:
            results["reason"] = "no_channels_configured"
        return results

    def _send_email(self, subject: str, body: str) -> dict[str, Any]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.NOTIFICATION_EMAIL_FROM
        msg["To"] = settings.NOTIFICATION_EMAIL_TO
        msg.set_content(body)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls(context=context)
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return {"ok": True}
        except Exception as exc:
            logger.warning("Email notification failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _send_slack(self, subject: str, body: str, payload: dict[str, Any]) -> dict[str, Any]:
        slack_payload = {
            "text": subject,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{subject}*"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"```{body}```"}},
            ],
        }
        return self._post_json(settings.SLACK_WEBHOOK_URL, slack_payload)

    def _send_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post_json(settings.NOTIFICATION_WEBHOOK_URL, payload)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                return {"ok": 200 <= response.status < 300, "status": response.status}
        except error.HTTPError as exc:
            logger.warning("Webhook notification failed: HTTP %s", exc.code)
            return {"ok": False, "error": f"HTTP {exc.code}"}
        except Exception as exc:
            logger.warning("Webhook notification failed: %s", exc)
            return {"ok": False, "error": str(exc)}
