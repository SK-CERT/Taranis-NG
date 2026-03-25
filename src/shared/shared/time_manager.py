"""This module provides functions to schedule jobs at specific intervals using the schedule library."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from threading import Event
    from typing import Any

    from schedule import Job

import threading
import time

import schedule

from shared.log_manager import logger


class SchedulerManager:
    """Class to manage scheduler jobs."""

    scheduler_stop_handler: Event | None = None

    @classmethod
    def init_scheduler(cls) -> None:
        """Initialize the scheduler."""
        if cls.scheduler_stop_handler is None:
            cls.scheduler_stop_handler = cls.run_scheduler()

    @staticmethod
    def schedule_job_every_day(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every day at a specific time."""
        logger.debug(f"Scheduling '{description}' for {interval} daily")
        job = schedule.every().day.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_minutes(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every X minutes."""
        logger.debug(f"Scheduling '{description}' for every {interval} minutes")
        job = schedule.every(interval).minutes.do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_monday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Monday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Monday {interval}")
        job = schedule.every().monday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_tuesday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Tuesday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Tuesday {interval}")
        job = schedule.every().tuesday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_wednesday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Wednesday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Wednesday {interval}")
        job = schedule.every().wednesday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_thursday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Thursday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Thursday {interval}")
        job = schedule.every().thursday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_friday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Friday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Friday {interval}")
        job = schedule.every().friday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_saturday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Saturday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Saturday {interval}")
        job = schedule.every().saturday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def schedule_job_on_sunday(interval: str, job_func: Callable[..., Any], description: str, *args, **kwargs) -> Job:  # noqa: ANN002, ANN003
        """Schedule a job to run every Sunday at a specific time."""
        logger.debug(f"Scheduling '{description}' for every Sunday {interval}")
        job = schedule.every().sunday.at(interval).do(job_func, *args, **kwargs)
        job.description = description
        return job

    @staticmethod
    def cancel_all_jobs() -> None:
        """Cancel all scheduled jobs in current thread."""
        logger.debug("Scheduler: cancel all jobs")
        schedule.clear()

    @classmethod
    def run_scheduler(cls) -> Event:
        """Run the scheduler in a separate thread."""
        scheduler_event = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls) -> None:
                while not scheduler_event.is_set():
                    try:
                        for job in schedule.get_jobs():
                            if job.should_run:
                                desc = getattr(job, "description", "N/A")
                                job._schedule_next_run()  # noqa: SLF001
                                logger.debug(
                                    f"Running scheduled job '{desc}', next run {job.next_run.strftime('%Y.%m.%d %H:%M')}",
                                )
                                job.run()
                        time.sleep(10)
                    except Exception as ex:
                        logger.error(f"Scheduler thread encountered an error: {ex}")

        scheduler_thread = ScheduleThread()
        scheduler_thread.start()
        logger.debug("Scheduler thread initialized")
        return scheduler_event
