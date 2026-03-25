"""Scheduler module to initialize the application and schedule tasks."""

import time

from app import create_app
from managers import auth_manager, sse_manager, tagcloud_manager
from shared.time_manager import SchedulerManager


def main() -> None:
    """Main function to initialize the application and schedule tasks."""
    app = create_app()

    with app.app_context():
        SchedulerManager.init_scheduler()
        tagcloud_manager.schedule(SchedulerManager, app)
        sse_manager.schedule(SchedulerManager, app)
        auth_manager.schedule(SchedulerManager, app)

    # Keep scheduler running
    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()
