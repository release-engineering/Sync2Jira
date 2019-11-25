#!/usr/bin/env python3
"""
This script is used to send emails
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DEFAULT_FROM = os.environ['DEFAULT_FROM']
DEFAULT_SERVER = os.environ['DEFAULT_SERVER']


def send_mail(recipients, subject, text, cc):
    """
    Sends email to recipients.

    :param List recipients: recipients of email
    :param String subject: subject of the email
    :param String text: HTML text
    :param String cc: cc of the email
    :param String text: text of the email
    :returns: Nothing
    """
    _cfg = {}
    _cfg.setdefault("server", DEFAULT_SERVER)
    _cfg.setdefault("from", DEFAULT_FROM)
    sender = _cfg["from"]
    msg = MIMEMultipart('related')
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    if cc:
        msg['Cc'] = ", ".join(cc)
    server = smtplib.SMTP(_cfg["server"])
    part = MIMEText(text, 'html', 'utf-8')
    msg.attach(part)

    server.sendmail(sender, recipients, msg.as_string())
    server.quit()
