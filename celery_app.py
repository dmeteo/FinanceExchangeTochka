import os
from celery import Celery

celery_app = Celery(
    "app",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

celery_app.conf.task_routes = {
    "tasks.match_order": {"queue": "matching"}
}

import tasks.match_order