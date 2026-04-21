import logging

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import COLLECT_HOUR, PUBLISH_HOUR
from .database import SessionLocal
from .services.pipeline import collect_candidates, publish_issue, purge_old_data

from .services.devs_pipeline import collect_dev_candidates, publish_dev_feed

# Weekly X handle discovery entrypoint. Slice 2 did not implement this;
# the weekly job is wired but will no-op with a warning until an entrypoint
# lands. Flagged to the user in the harmonization report.
try:
    from .services.devs_pipeline import discover_x_handles  # type: ignore
except ImportError:  # pragma: no cover - discovery entrypoint not yet implemented
    discover_x_handles = None  # type: ignore

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_devs_collect() -> None:
    db = SessionLocal()
    try:
        collect_dev_candidates(db)
    except Exception:
        logger.exception("devs_collect job failed")
    finally:
        db.close()


def _run_devs_publish() -> None:
    db = SessionLocal()
    try:
        publish_dev_feed(db)
    except Exception:
        logger.exception("devs_publish job failed")
    finally:
        db.close()


def _run_devs_handle_discovery() -> None:
    if discover_x_handles is None:
        logger.warning("devs_handle_discovery: discover_x_handles not available; skipping")
        return
    db = SessionLocal()
    try:
        discover_x_handles(db)
    except Exception:
        logger.exception("devs_handle_discovery job failed")
    finally:
        db.close()


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
        trigger=CronTrigger(hour=PUBLISH_HOUR, timezone=pytz.utc),
        id="daily_publish",
        name="Daily issue publication (rolling candidate pool)",
        replace_existing=True,
    )

    _scheduler.add_job(
        purge_old_data,
        trigger=CronTrigger(hour=COLLECT_HOUR, minute=30, timezone=pytz.utc),
        id="daily_purge",
        name="Purge data older than retention period",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_devs_collect,
        trigger=CronTrigger(hour=COLLECT_HOUR, minute=5, timezone=pytz.utc),
        id="devs_collect",
        name="Daily devs feed collection (HN + GitHub + X)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    _scheduler.add_job(
        _run_devs_publish,
        trigger=CronTrigger(hour=PUBLISH_HOUR, minute=5, timezone=pytz.utc),
        id="devs_publish",
        name="Daily devs feed publish orchestrator",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    _scheduler.add_job(
        _run_devs_handle_discovery,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=pytz.utc),
        id="devs_handle_discovery",
        name="Weekly X handle discovery (Sun 02:00 UTC)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — collect daily at %02d:00 UTC, publish daily at %02d:00 UTC, "
        "purge daily at %02d:30 UTC, devs_collect %02d:05, devs_publish %02d:05, "
        "devs_handle_discovery Sundays 02:00",
        COLLECT_HOUR,
        PUBLISH_HOUR,
        COLLECT_HOUR,
        COLLECT_HOUR,
        PUBLISH_HOUR,
    )


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
