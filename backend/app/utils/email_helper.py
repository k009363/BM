"""
SMTP email helper.
Credentials and enabled/disabled flag are stored in site_config (key='smtp').
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_smtp_cfg():
    try:
        from app.database.mongo_db import db
        cfg = db.site_config.find_one(key='smtp')
        if cfg and cfg.get('enabled') == 'True' and cfg.get('host') and cfg.get('from_email'):
            return cfg
    except Exception:
        pass
    return None


def send_email(to_email: str, subject: str, body_html: str, body_text: str = '') -> bool:
    cfg = _get_smtp_cfg()
    if not cfg:
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{cfg.get('from_name', 'BlogMedia')} <{cfg['from_email']}>"
        msg['To']      = to_email

        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        host     = cfg.get('host', '')
        port     = int(cfg.get('port', 587))
        username = cfg.get('username', '')
        password = cfg.get('password', '')

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        if username:
            server.login(username, password)

        server.sendmail(cfg['from_email'], to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f'[email] send failed: {e}')
        return False
