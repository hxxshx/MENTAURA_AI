"""
Email Service for Mentaura Platform.
Handles reliable dispatch of email verification OTP codes:
1. Resend REST API (HTTPS port 443 - works on Render Free & all cloud providers)
2. Brevo REST API (HTTPS port 443 - works on Render Free & all cloud providers)
3. Gmail SMTP TLS/SSL (standard SMTP port 587/465)
4. Graceful fallback when cloud hosting firewalls block SMTP ports.
"""
import smtplib
import logging
import json
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.app.config import settings

logger = logging.getLogger("mentaura.email")


def _send_via_resend(to_email: str, html_content: str, text_content: str) -> bool:
    """Send email via Resend HTTPS REST API (Port 443)."""
    api_key = (settings.RESEND_API_KEY or "").strip()
    if not api_key:
        return False
    try:
        from_addr = (settings.GMAIL_ADDRESS or "onboarding@resend.dev").strip()
        if not from_addr.startswith("onboarding@resend.dev") and "@" not in from_addr:
            from_addr = "onboarding@resend.dev"

        payload = {
            "from": f"Mentaura Support <{from_addr}>",
            "to": [to_email],
            "subject": "Verify your Mentaura account",
            "html": html_content,
            "text": text_content,
        }
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mentaura-App/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status in (200, 201):
                logger.info(f"OTP successfully dispatched via Resend HTTPS API to {to_email}.")
                print(f"\n[EMAIL DISPATCH] Real OTP email sent via Resend API to {to_email}.\n", flush=True)
                return True
    except Exception as e:
        logger.warning(f"Resend HTTP dispatch error: {e}")
    return False


def _send_via_brevo(to_email: str, html_content: str, text_content: str) -> bool:
    """Send email via Brevo HTTPS REST API (Port 443)."""
    api_key = (settings.BREVO_API_KEY or "").strip()
    if not api_key:
        return False
    try:
        sender_email = (settings.GMAIL_ADDRESS or "support@mentaura.org").strip()
        payload = {
            "sender": {"name": "Mentaura Support", "email": sender_email},
            "to": [{"email": to_email}],
            "subject": "Verify your Mentaura account",
            "htmlContent": html_content,
            "textContent": text_content,
        }
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mentaura-App/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status in (200, 201):
                logger.info(f"OTP successfully dispatched via Brevo HTTPS API to {to_email}.")
                print(f"\n[EMAIL DISPATCH] Real OTP email sent via Brevo API to {to_email}.\n", flush=True)
                return True
    except Exception as e:
        logger.warning(f"Brevo HTTP dispatch error: {e}")
    return False


def _send_via_smtp(to_email: str, msg: MIMEMultipart, gmail_user: str, gmail_pwd: str) -> bool:
    """Send email via SMTP with tight timeout to avoid blocking on Render Free."""
    host = settings.SMTP_HOST or "smtp.gmail.com"
    port = settings.SMTP_PORT or 587
    timeout = settings.SMTP_TIMEOUT or 3

    try:
        server = smtplib.SMTP(host, port, timeout=timeout)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(gmail_user, [to_email], msg.as_string())
        server.quit()
        logger.info(f"OTP verification email successfully dispatched via SMTP to {to_email}.")
        print(f"\n[EMAIL DISPATCH] Real OTP email successfully sent to {to_email} via Gmail SMTP.\n", flush=True)
        return True
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.warning(f"Gmail SMTP Authentication Failed (535 BadCredentials): {auth_err}")
        return False
    except (TimeoutError, smtplib.SMTPConnectError, OSError) as net_err:
        logger.warning(
            f"SMTP Connection Blocked/Timed out ({type(net_err).__name__}). "
            "Note: Render Free Tier firewalls outbound SMTP ports (25, 465, 587). "
            "Using fallback verification delivery."
        )
        return False
    except Exception as e:
        logger.warning(f"SMTP dispatch error: {type(e).__name__} ({e})")
        return False


def send_otp_email(to_email: str, otp_code: str, user_name: Optional[str] = None) -> bool:
    """
    Send a 6-digit OTP verification code to the user's email address.
    1. Tries HTTPS email APIs first (Resend / Brevo) - guaranteed on Render Free.
    2. Tries standard SMTP (port 587/465).
    3. Returns True if email was successfully delivered to inbox, False if blocked/failed.
    """
    display_name = user_name.strip() if user_name else "User"
    gmail_user = (settings.GMAIL_ADDRESS or "").strip()
    gmail_pwd = (settings.GMAIL_APP_PASSWORD or "").replace(" ", "").strip()

    # Plain-text version
    text_content = f"""Hello {display_name},

Thank you for registering with Mentaura — Case-Aware Support Intelligence Platform.

Your 6-digit account verification code is: {otp_code}

This code will expire in 10 minutes. If you did not request this account creation, please ignore this email.

Warm regards,
Mentaura Support Intelligence Team
"""

    # Rich HTML version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7f9fc; margin: 0; padding: 24px; color: #1e293b; }}
    .email-container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .email-header {{ background: #2B1552; padding: 28px 32px; text-align: center; }}
    .email-header h1 {{ color: #ffffff; font-size: 22px; font-weight: 700; margin: 0; letter-spacing: 0.5px; }}
    .email-header p {{ color: #e2d9f3; font-size: 13px; margin: 6px 0 0 0; }}
    .email-body {{ padding: 32px; }}
    .otp-badge {{ display: inline-block; background: #f1f5f9; border: 2px dashed #6366f1; border-radius: 8px; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #2B1552; padding: 12px 24px; margin: 20px 0; text-align: center; }}
    .timer-notice {{ display: flex; align-items: center; background: #fffbeb; border: 1px solid #fef3c7; color: #92400e; padding: 10px 14px; border-radius: 6px; font-size: 13px; margin-bottom: 20px; }}
    .email-footer {{ background: #f8fafc; padding: 20px 32px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <h1>MENTAURA</h1>
      <p>Case-Aware Support Intelligence Platform</p>
    </div>
    <div class="email-body">
      <h2 style="font-size: 18px; color: #0f172a; margin-top: 0;">Verify Your Email Address</h2>
      <p style="font-size: 14px; line-height: 1.6; color: #475569;">
        Hello {display_name},<br>
        Please use the following 6-digit verification code to activate your Mentaura account:
      </p>
      
      <div style="text-align: center;">
        <div class="otp-badge">{otp_code}</div>
      </div>

      <div class="timer-notice">
        <span>⏱️ <strong>Valid for 10 minutes:</strong> For your security, this code will expire shortly.</span>
      </div>

      <p style="font-size: 13px; line-height: 1.5; color: #64748b;">
        If you did not initiate this registration, no further action is required. Your security and privacy are strictly safeguarded.
      </p>
    </div>
    <div class="email-footer">
      This is an automated system message from Mentaura. Please do not reply directly to this email.
    </div>
  </div>
</body>
</html>
"""

    # 1. Try Resend HTTPS API (Port 443 - unblocked on Render Free)
    if _send_via_resend(to_email, html_content, text_content):
        return True

    # 2. Try Brevo HTTPS API (Port 443 - unblocked on Render Free)
    if _send_via_brevo(to_email, html_content, text_content):
        return True

    # 3. Try standard Gmail SMTP (Port 587/465)
    if gmail_user and gmail_pwd:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your Mentaura account"
        msg["From"] = f"Mentaura Support <{gmail_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if _send_via_smtp(to_email, msg, gmail_user, gmail_pwd):
            return True

    # Safe fallback output for logs
    print(f"\n{'='*60}", flush=True)
    print(f"[OTP DELIVERY] Verification code for {to_email}: {otp_code}", flush=True)
    print(f"{'='*60}\n", flush=True)
    return False
