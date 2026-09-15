from celery import shared_task

from . import services


@shared_task(name="communication.dispatch")
def dispatch(log_id: str) -> None:
    services.dispatch_now(log_id)
