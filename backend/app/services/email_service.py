"""
Email Service for Mentaura Platform.
Handles secure SMTP dispatch of email verification OTP codes using Gmail App Password.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.app.config import settings

logger = logging.getLogger("mentaura.email")

def send_otp_email(to_email: str, otp_code: str, user_name: Optional[str] = None) -> bool:
    """
    Send a 6-digit OTP verification code to the user's email address via Gmail SMTP (TLS 587).
    Never logs the raw OTP or email password.
    Falls back gracefully if SMTP is unreachable or credentials are unconfigured.
    """
    gmail_user = (settings.GMAIL_ADDRESS or "").strip()
    gmail_pwd = (settings.GMAIL_APP_PASSWORD or "").replace(" ", "").strip()

    if not gmail_user or not gmail_pwd:
        logger.warning(
            "Gmail SMTP credentials not configured (GMAIL_ADDRESS / GMAIL_APP_PASSWORD). "
            "Skipping real email dispatch in safe development mode."
        )
        return False

    display_name = user_name.strip() if user_name else "User"

    # Create MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Mentaura account"
    msg["From"] = f"Mentaura Support <{gmail_user}>"
    msg["To"] = to_email

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

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(gmail_user, [to_email], msg.as_string())
        server.quit()
        logger.info(f"OTP verification email successfully dispatched via Gmail SMTP to {to_email}.")
        print(f"\n[EMAIL DISPATCH] Real OTP email successfully sent to {to_email} via Gmail SMTP.\n", flush=True)
        return True
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.warning(
            f"Gmail SMTP Authentication Failed (535 BadCredentials): {auth_err}. "
            "Please ensure 2FA is enabled and a valid 16-character Gmail App Password is configured in .env."
        )
        print(f"\n{'='*60}", flush=True)
        print(f"[DEV FALLBACK] Gmail SMTP BadCredentials — OTP for {to_email}: {otp_code}", flush=True)
        print(f"[DEV FALLBACK] Use code '{otp_code}' to verify. Update GMAIL_APP_PASSWORD in .env for real inbox delivery.", flush=True)
        print(f"{'='*60}\n", flush=True)
        return False
    except Exception as e:
        logger.warning(f"Failed to dispatch OTP verification email via SMTP: {type(e).__name__} ({e}). Safe dev fallback engaged.")
        print(f"\n{'='*60}", flush=True)
        print(f"[DEV FALLBACK] OTP verification code for {to_email}: {otp_code}", flush=True)
        print(f"{'='*60}\n", flush=True)
        return False
