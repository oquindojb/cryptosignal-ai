from .config import PUSH_ENABLED, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_EMAIL
from .db import SessionLocal, PushSubscription
import json

async def notify_signal(symbol, action, score, confidence, headline):
    if not (PUSH_ENABLED and VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY): return 0
    try:
        from pywebpush import webpush, WebPushException
    except Exception: return 0
    db=SessionLocal(); sent=0
    try:
        rows=db.query(PushSubscription).all()
        payload=json.dumps({'title':f'CryptoSignal · {symbol} {action}','body':f'{headline[:110]} · Score {score}/100 · Confidence {confidence}%','url':'/'})
        for row in rows:
            sub={'endpoint':row.endpoint,'keys':{'p256dh':row.p256dh,'auth':row.auth}}
            try:
                webpush(subscription_info=sub,data=payload,vapid_private_key=VAPID_PRIVATE_KEY,vapid_claims={'sub':VAPID_EMAIL})
                sent+=1
            except Exception as e:
                if '410' in str(e) or '404' in str(e): db.delete(row)
        db.commit(); return sent
    finally: db.close()
