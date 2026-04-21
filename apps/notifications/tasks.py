from celery import shared_task
from .sms import EskizClient, render_sms


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue='default')
def send_sms(self, phone: str, message: str) -> dict:
    try:
        return EskizClient().send(phone, message)
    except RuntimeError as exc:
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=10, queue='default')
def send_welcome_sms(self, phone: str, name: str) -> None:
    try:
        message = render_sms('WELCOME', name=name)
        EskizClient().send(phone, message)
    except RuntimeError as exc:
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
