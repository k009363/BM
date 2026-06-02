"""
Web Push notification helper.
VAPID private key is read from env.
Enabled/disabled and VAPID email can be overridden from DB settings.
Expired subscriptions (HTTP 410) are auto-removed.
"""
import json
import os

from pywebpush import webpush, WebPushException
from app.database.mongo_db import db

_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')


def _push_config():
    """Return (enabled, vapid_claims). DB settings override env defaults."""
    try:
        cfg = db.site_config.find_one(key='push')
        if cfg:
            if cfg.get('enabled') == 'False':
                return False, None
            email = cfg.get('vapid_email') or os.getenv('VAPID_EMAIL', 'admin@blogmedia.com')
        else:
            email = os.getenv('VAPID_EMAIL', 'admin@blogmedia.com')
    except Exception:
        email = os.getenv('VAPID_EMAIL', 'admin@blogmedia.com')
    return True, {'sub': f'mailto:{email}'}


def send_push(user_id: str, title: str, body: str, url: str = '/') -> None:
    if not _PRIVATE_KEY:
        return
    enabled, claims = _push_config()
    if not enabled:
        return
    subs = db.push_subscriptions.find(user_id=user_id)
    for s in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': s['endpoint'],
                    'keys': {'p256dh': s['p256dh'], 'auth': s['auth']},
                },
                data=json.dumps({'title': title, 'body': body, 'url': url}),
                vapid_private_key=_PRIVATE_KEY,
                vapid_claims=claims,
                ttl=86400,
            )
        except WebPushException as e:
            if e.response is not None and e.response.status_code == 410:
                db.push_subscriptions.delete_by_id(s['id'])
        except Exception:
            pass
