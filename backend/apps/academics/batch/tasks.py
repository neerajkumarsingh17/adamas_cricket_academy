from celery import shared_task

from . import services


@shared_task(name="batch.generate_sessions")
def generate_sessions() -> None:
    services.generate_sessions(days=28)
