"""Service d'envoi d'email via SMTP (MailHog en dev, vrai SMTP en prod)."""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

from app.core.config import settings

log = logging.getLogger(__name__)


@dataclass
class EmailResult:
    sent: bool
    error: Optional[str] = None


def _send_sync(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> EmailResult:
    if settings.smtp_test_mode:
        log.info("[SMTP test_mode] To=%s | Subject=%s", to_email, subject)
        return EmailResult(sent=True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        return EmailResult(sent=True)
    except Exception as e:
        log.warning("SMTP send failed to %s : %s", to_email, e)
        return EmailResult(sent=False, error=str(e))


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> EmailResult:
    """Envoie un email de manière non-bloquante (run dans thread pool)."""
    return await asyncio.to_thread(_send_sync, to_email, subject, html_body, text_body)


async def send_otp_email(
    db, *, tenant_id, to_email: str, code: str, validity_minutes: int,
) -> EmailResult:
    """Envoie le code OTP à 6 chiffres au sociétaire.

    Le subject et le contenu sont injectés depuis les settings tenant pour
    cohérence du branding (assistant_name, support_email).
    """
    from app.services import settings_service
    try:
        assistant_name = await settings_service.get_value(
            db, tenant_id, "general", "assistant_name"
        )
        support_email = await settings_service.get_value(
            db, tenant_id, "general", "support_email"
        )
    except Exception:
        assistant_name = settings.smtp_from_name
        support_email = settings.smtp_from_email

    subject = f"[MA2E] Votre code de vérification : {code}"
    text_body = (
        f"Bonjour,\n\n"
        f"Voici votre code de vérification {assistant_name} :\n\n"
        f"   {code}\n\n"
        f"Ce code est valable {validity_minutes} minutes. Ne le partagez avec personne.\n\n"
        f"Si vous n'avez pas demandé ce code, ignorez cet email ou contactez {support_email}.\n\n"
        f"— Équipe MA2E"
    )
    html_body = f"""\
<!DOCTYPE html>
<html lang="fr">
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #F6FAF7; padding: 24px; color: #1a1a1a;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 6px; padding: 32px; border: 1px solid #e5e7eb;">
    <h2 style="margin: 0 0 16px; color: #2D5F4F; font-size: 18px;">Code de vérification {assistant_name}</h2>
    <p style="margin: 0 0 16px; font-size: 14px; line-height: 1.6;">
      Voici votre code de vérification :
    </p>
    <div style="background: #F6FAF7; border: 1px dashed #2D5F4F; border-radius: 4px; padding: 16px; text-align: center; font-family: 'SF Mono', Consolas, monospace; font-size: 28px; letter-spacing: 6px; color: #2D5F4F; font-weight: 600;">
      {code}
    </div>
    <p style="margin: 16px 0; font-size: 13px; color: #6b7280; line-height: 1.6;">
      Ce code est valable <strong>{validity_minutes} minutes</strong>. Ne le partagez avec personne.
    </p>
    <p style="margin: 24px 0 0; font-size: 12px; color: #9ca3af; line-height: 1.5;">
      Si vous n'avez pas demandé ce code, ignorez cet email ou contactez
      <a href="mailto:{support_email}" style="color: #2D5F4F;">{support_email}</a>.
    </p>
  </div>
  <p style="margin: 16px auto 0; max-width: 480px; font-size: 11px; color: #9ca3af; text-align: center;">
    Mutuelle des Agents de l'Eau et de l'Électricité — Côte d'Ivoire
  </p>
</body>
</html>
"""
    return await send_email(to_email, subject, html_body, text_body)
