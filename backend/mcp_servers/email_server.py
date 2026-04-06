import smtplib
from email.mime.text import MIMEText


def send_email(receiver, subject, message):

    sender_email = "actionorientedai@gmail.com"
    app_password = "aiqq vkfv qjgk svpd"

    msg = MIMEText(message)

    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(sender_email, app_password)

        server.sendmail(sender_email, receiver, msg.as_string())

        server.quit()

        return f"Email successfully sent to {receiver}"

    except Exception as e:

        return f"Email failed: {str(e)}"