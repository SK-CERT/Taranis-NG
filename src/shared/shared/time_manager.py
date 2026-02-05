"""This module provides functions to schedule jobs at specific intervals using the schedule library."""

import threading
import time

import schedule


def schedule_job_every_day(interval, job_func, *args, **kwargs):
    """Schedule a job to run every day at a specific time."""
    return schedule.every().day.at(interval).do(job_func, *args, **kwargs)


def schedule_job_minutes(interval, job_func, *args, **kwargs):
    """Schedule a job to run every X minutes."""
    return schedule.every(interval).minutes.do(job_func, *args, **kwargs)


def schedule_job_on_monday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Monday at a specific time."""
    return schedule.every().monday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_tuesday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Tuesday at a specific time."""
    return schedule.every().tuesday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_wednesday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Wednesday at a specific time."""
    return schedule.every().wednesday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_thursday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Thursday at a specific time."""
    return schedule.every().thursday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_friday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Friday at a specific time."""
    return schedule.every().friday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_saturday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Saturday at a specific time."""
    return schedule.every().saturday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_sunday(interval, job_func, *args, **kwargs):
    """Schedule a job to run every Sunday at a specific time."""
    return schedule.every().sunday.at(interval).do(job_func, *args, **kwargs)


def cancel_all_jobs():
    """Cancel all scheduled jobs in current thread."""
    schedule.clear()


def run_scheduler():
    """Run the scheduler in a separate thread."""
    scheduler_event = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            print("Scheduler thread started.", flush=True)
            while not scheduler_event.is_set():
                try:
                    # print(f"Registered jobs: {schedule.jobs}", flush=True)
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as ex:
                    print(f"Scheduler thread encountered an error: {ex}", flush=True)

    scheduler_thread = ScheduleThread()
    scheduler_thread.start()
    print("Scheduler thread initialized.", flush=True)
    return scheduler_event


scheduler_stop_handler = run_scheduler()
