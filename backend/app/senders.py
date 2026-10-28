"""Channel delivery adapters (NOTIFICATIONS.md Part E.2).

One uniform `send(channel, notif) -> (status, error)` per out-of-app channel. Every adapter is **credential-gated**:
the actual providers (Expo push, an SMTP relay, an India DLT SMS BSP, a WhatsApp BSP) are external accounts, not
code, so when their env config or the recipient is missing the adapter returns ("skipped", reason) and nothing
breaks. Add the env vars and sends start flowing — no code change. This keeps the architecture complete and
testable now while the DLT/WhatsApp/SES accounts are being provisioned.

Transport style matches interop.fire(): short-timeout urllib, no persistent connections, safe on the 512MB box.

Env config:
  Push  — EXPO_ACCESS_TOKEN (optional; Expo Push API works without for most projects)
  Email — TELOMY_SMTP_HOST, TELOMY_SMTP_PORT, TELOMY_SMTP_USER, TELOMY_SMTP_PASS, TELOMY_SMTP_FROM
  SMS   — TELOMY_SMS_URL, TELOMY_SMS_KEY, TELOMY_SMS_SENDER   (generic JSON POST; DLT header/template per BSP)
  WA    — TELOMY_WA_URL, TELOMY_WA_TOKEN                      (BSP / Meta Cloud API endpoint)
"""
import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from . import db, engine

_TIMEOUT = 5
_EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _profile() -> dict:
    try:
        return engine.profile() or {}
    except Exception:
        return {}


def _post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[str, str | None]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            if 200 <= r.status < 300:
                return "sent", None
            return "error", f"HTTP {r.status}"
    except Exception as exc:  # noqa: BLE001
        return "error", f"{type(exc).__name__}: {exc}"


# --- push (Expo) -------------------------------------------------------------------------------------------------

def _push(notif: dict) -> tuple[str, str | None]:
    tokens = [r["token"] for r in db.rows("SELECT token FROM push_tokens")]
    if not tokens:
        return "skipped", "no push tokens"
    headers = {}
    if os.environ.get("EXPO_ACCESS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['EXPO_ACCESS_TOKEN']}"
    messages = [{"to": t, "title": notif["title"], "body": notif["body"],
                 "priority": "high" if notif["priority"] in ("critical", "high") else "default",
                 "data": {"route": notif.get("route"), "kind": notif.get("kind"), "id": notif.get("id")}}
                for t in tokens]
    return _post_json(_EXPO_URL, messages if len(messages) > 1 else messages[0], headers)


# --- email (SMTP) ------------------------------------------------------------------------------------------------

def _email(notif: dict) -> tuple[str, str | None]:
    host = os.environ.get("TELOMY_SMTP_HOST")
    sender = os.environ.get("TELOMY_SMTP_FROM")
    if not host or not sender:
        return "skipped", "no SMTP config"
    to = _profile().get("email")
    if not to:
        return "skipped", "no recipient email"
    msg = EmailMessage()
    msg["Subject"] = notif["title"]
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(notif["body"])
    try:
        port = int(os.environ.get("TELOMY_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=_TIMEOUT) as s:
            s.starttls(context=ssl.create_default_context())
            if os.environ.get("TELOMY_SMTP_USER"):
                s.login(os.environ["TELOMY_SMTP_USER"], os.environ.get("TELOMY_SMTP_PASS", ""))
            s.send_message(msg)
        return "sent", None
    except Exception as exc:  # noqa: BLE001
        return "error", f"{type(exc).__name__}: {exc}"


# --- SMS (India DLT BSP) -----------------------------------------------------------------------------------------

def _sms(notif: dict) -> tuple[str, str | None]:
    url = os.environ.get("TELOMY_SMS_URL")
    if not url:
        return "skipped", "no SMS config"
    phone = notif.get("to") or _profile().get("phone")  # 'to' override for pre-auth sends (e.g. OTP)
    if not phone:
        return "skipped", "no recipient phone"
    # Generic JSON POST; the exact body/DLT template id is BSP-specific and configured by the BSP integration.
    payload = {"to": phone, "sender": os.environ.get("TELOMY_SMS_SENDER", "TELOMY"),
               "message": f"{notif['title']}. {notif['body']}"}
    return _post_json(url, payload, {"Authorization": f"Bearer {os.environ.get('TELOMY_SMS_KEY', '')}"})


# --- WhatsApp (BSP) ----------------------------------------------------------------------------------------------

def _whatsapp(notif: dict) -> tuple[str, str | None]:
    url = os.environ.get("TELOMY_WA_URL")
    if not url:
        return "skipped", "no WhatsApp config"
    phone = notif.get("to") or _profile().get("phone")
    if not phone:
        return "skipped", "no recipient phone"
    payload = {"to": phone, "type": "text", "text": {"body": f"{notif['title']}\n{notif['body']}"}}
    return _post_json(url, payload, {"Authorization": f"Bearer {os.environ.get('TELOMY_WA_TOKEN', '')}"})


_ADAPTERS = {"push": _push, "email": _email, "sms": _sms, "whatsapp": _whatsapp}


def send(channel: str, notif: dict) -> tuple[str, str | None]:
    fn = _ADAPTERS.get(channel)
    if fn is None:
        return "skipped", f"unknown channel {channel}"
    return fn(notif)


def configured_channels() -> list[str]:
    """Which channels have provider credentials set (for diagnostics / the preferences UI)."""
    out = ["push"]  # Expo works without a key
    if os.environ.get("TELOMY_SMTP_HOST"):
        out.append("email")
    if os.environ.get("TELOMY_SMS_URL"):
        out.append("sms")
    if os.environ.get("TELOMY_WA_URL"):
        out.append("whatsapp")
    return out
