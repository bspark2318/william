import logging

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import COLLECT_HOUR, PUBLISH_DAY, PUBLISH_HOUR
from .services.pipeline import collect_candidates, publish_issue, purge_old_data

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone=pytz.utc)

    _scheduler.add_job(
        collect_candidates,
        trigger=CronTrigger(hour=COLLECT_HOUR, timezone=pytz.utc),
        id="daily_collect",
        name="Daily news & video collection",
        replace_existing=True,
    )

    _scheduler.add_job(
        publish_issue,
        trigger=CronTrigger(day_of_week=PUBLISH_DAY[:3].lower(), hour=PUBLISH_HOUR, timezone=pytz.utc),
        id="weekly_publish",
        name="Weekly issue publication",
        replace_existing=True,
    )

    _scheduler.add_job(
        purge_old_data,
        trigger=CronTrigger(hour=COLLECT_HOUR, minute=30, timezone=pytz.utc),
        id="daily_purge",
        name="Purge data older than retention period",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — collect daily at %02d:00 UTC, publish %s at %02d:00 UTC, purge daily at %02d:30 UTC",
        COLLECT_HOUR,
        PUBLISH_DAY,
        PUBLISH_HOUR,
        COLLECT_HOUR,
    )


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
