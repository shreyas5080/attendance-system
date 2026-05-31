from email.message import EmailMessage
import os
import smtplib


def send_otp_email(to_email, otp):
    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USERNAME")
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    port = int(os.getenv("SMTP_PORT", "587"))
    app_env = os.getenv("APP_ENV", "development").lower()

    if not host or not sender:
        if app_env == "production":
            return False, "OTP email service is not configured."
        return True, f"Development OTP: {otp}"

    message = EmailMessage()
    message["Subject"] = "Your Attendly verification code"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your Attendly verification code is {otp}.\n\n"
        "This code expires in 10 minutes. If you did not request it, ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except OSError as error:
        return False, f"Could not send OTP email: {error}"
    except smtplib.SMTPException as error:
        return False, f"Could not send OTP email: {error}"

    return True, "OTP sent to your email."
