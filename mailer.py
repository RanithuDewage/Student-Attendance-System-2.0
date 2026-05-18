from pathlib import Path
import mimetypes
import smtplib
import ssl
from email.message import EmailMessage


def send_report_email(settings: dict, subject: str, body: str, attachments=None):
    """
    Send an email with optional attachments.

    Expected settings keys:
      - smtp_host
      - smtp_port
      - smtp_use_tls
      - smtp_use_ssl   (optional)
      - sender_email
      - sender_password
      - receiver_email

    Notes:
      - Gmail users should use an App Password.
      - If smtp_use_tls is True, STARTTLS is used.
      - If smtp_use_ssl is True, SSL connection is used.
    """
    host = str(settings.get("smtp_host", "")).strip()
    port = int(settings.get("smtp_port", 587))
    use_tls = bool(settings.get("smtp_use_tls", True))
    use_ssl = bool(settings.get("smtp_use_ssl", False))

    sender = str(settings.get("sender_email", "")).strip()
    password = str(settings.get("sender_password", "")).strip()
    receiver = str(settings.get("receiver_email", "")).strip()

    missing = []
    if not host:
        missing.append("smtp_host")
    if not sender:
        missing.append("sender_email")
    if not password:
        missing.append("sender_password")
    if not receiver:
        missing.append("receiver_email")

    if missing:
        raise RuntimeError(f"SMTP settings incomplete: {', '.join(missing)}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(body)

    # Attach files if provided
    for file_path in attachments or []:
        p = Path(file_path)

        if not p.exists() or not p.is_file():
            continue

        mime_type, _ = mimetypes.guess_type(str(p))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        try:
            msg.add_attachment(
                p.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=p.name,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to attach file '{p.name}': {e}")

    context = ssl.create_default_context()

    try:
        if use_ssl:
            # SSL mode usually used with port 465
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.login(sender, password)
                server.send_message(msg)
        elif use_tls:
            # STARTTLS mode usually used with port 587
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(sender, password)
                server.send_message(msg)
        else:
            # Plain SMTP - not recommended unless your server requires it
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.login(sender, password)
                server.send_message(msg)

    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP authentication failed. Check email and app password.")
    except smtplib.SMTPConnectError:
        raise RuntimeError("Could not connect to SMTP server.")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP error: {e}")
    except Exception as e:
        raise RuntimeError(f"Email sending failed: {e}")

    return True