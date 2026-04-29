from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_reminder_scan() -> None:
    from app.database import SessionLocal
    from app.services.reminders import scan

    db = SessionLocal()
    try:
        sent = scan(db)
        db.commit()
        logger.info("Reminder scan complete: %d reminders sent", sent)
    except Exception:
        logger.exception("Reminder scan failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_run_reminder_scan, "cron", hour=7, minute=0)
    _scheduler.start()
    logger.info("APScheduler started (reminder scan at 07:00 daily)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
