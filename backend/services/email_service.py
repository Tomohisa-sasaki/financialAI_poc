
from __future__ import annotations
import base64, smtplib, ssl, re
from email.message import EmailMessage
from core.config import get_settings
import requests

_EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_email(s: str) -> bool:
    return bool(_EMAIL_RX.match(s or ""))


def send_pdf_via_email(to: str, subject: str, text: str, pdf_bytes: bytes) -> bool:
    s = get_settings()
    if not _is_email(to):
        return False
    subject = subject or "Financial Report"
    text = text or "Please see attached report."

    # 1) SendGrid (if API key available)
    if s.SENDGRID_API_KEY:
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": (s.SMTP_FROM or "no-reply@example.com")},
            "subject": subject,
            "content": [{"type": "text/plain", "value": text}],
            "attachments": [
                {
                    "content": base64.b64encode(pdf_bytes).decode(),
                    "filename": "report.pdf",
                    "type": "application/pdf",
                    "disposition": "attachment",
                }
            ],
        }
        try:
            r = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {s.SENDGRID_API_KEY}"},
                timeout=20,
            )
            return r.status_code in (200, 202)
        except Exception:
            return False

    # 2) SMTP (if host provided)
    if s.SMTP_HOST:
        try:
            msg = EmailMessage()
            msg["From"] = s.SMTP_FROM or s.SMTP_USER or "report@localhost"
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(text)
            msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="report.pdf")

            context = ssl.create_default_context()
            with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=30) as smtp:
                if s.SMTP_USE_TLS:
                    try:
                        smtp.starttls(context=context)
                    except Exception:
                        # continue without TLS if server doesn't support it (optional)
                        pass
                if s.SMTP_USER and s.SMTP_PASS:
                    smtp.login(s.SMTP_USER, s.SMTP_PASS)
                smtp.send_message(msg)
                return True
        except Exception:
            return False

    return False
