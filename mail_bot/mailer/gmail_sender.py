from __future__ import annotations

import os
import smtplib
from collections.abc import Iterable
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid

from ..models import SendResult
from ..security import sanitize_header, validate_recipient_email


def send_mail(
    gmail_address: str,
    app_password: str,
    to_email: str,
    subject: str,
    body: str,
    cv_path: str | None = None,
    attachment_paths: Iterable[str] | None = None,
    thread_reference: str | None = None,
) -> SendResult:
    try:
        safe_to = validate_recipient_email(to_email)
        safe_subject = sanitize_header(subject, "Konu")
        safe_from = validate_recipient_email(gmail_address)
        
        msg_id = make_msgid(domain=gmail_address.split("@")[-1])
        
        message = MIMEMultipart()
        message["From"] = safe_from
        message["To"] = safe_to
        message["Subject"] = str(Header(safe_subject, "utf-8"))
        message["Message-ID"] = msg_id
        
        if thread_reference:
            message["In-Reply-To"] = thread_reference
            message["References"] = thread_reference

        message.attach(MIMEText(body, "plain", "utf-8"))

        paths = list(attachment_paths or [])
        if cv_path and cv_path not in paths:
            paths.insert(0, cv_path)
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as file_handle:
                attachment = MIMEApplication(file_handle.read(), _subtype="pdf")
                safe_filename = sanitize_header(os.path.basename(path), "Dosya adi")
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=safe_filename,
                )
                message.attach(attachment)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(safe_from, app_password)
            server.sendmail(safe_from, safe_to, message.as_string())
        return SendResult(ok=True, message_id=msg_id)
    except ValueError as exc:
        return SendResult(ok=False, error_message=str(exc))
    except smtplib.SMTPAuthenticationError as exc:
        return SendResult(ok=False, error_message="Uygulama sifresi hatali.", smtp_code=exc.smtp_code)
    except Exception as exc:
        code = getattr(exc, "smtp_code", None)
        return SendResult(ok=False, error_message=str(exc), smtp_code=code)


def validate_gmail_credentials(gmail_address: str, app_password: str) -> SendResult:
    try:
        safe_from = validate_recipient_email(gmail_address)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(safe_from, app_password)
        return SendResult(ok=True)
    except ValueError as exc:
        return SendResult(ok=False, error_message=str(exc))
    except smtplib.SMTPAuthenticationError as exc:
        return SendResult(ok=False, error_message="Uygulama sifresi hatali.", smtp_code=exc.smtp_code)
    except Exception as exc:
        code = getattr(exc, "smtp_code", None)
        return SendResult(ok=False, error_message=str(exc), smtp_code=code)
