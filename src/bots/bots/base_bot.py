"""BaseBot class represents the base abstract type for all bots."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.bot_preset import BotPreset

import datetime
import time
from http import HTTPStatus

from remote.core_api import CoreApi
from shared.common import TZ
from shared.log_manager import create_logger, logger
from shared.schema import bot, bot_preset
from shared.time_manager import SchedulerManager


class BaseBot:
    """BaseBot class represents the base abstract type for all bots."""

    bot_type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    def __init__(self) -> None:
        """Initialize the BaseBot class."""
        self.parameters = []
        self.bot_presets = []

    def get_info(self) -> dict:
        """Return the information of the bot.

        Returns:
            (dict): The information of the bot.
        """
        info_schema = bot.BotSchema()
        return info_schema.dump(self)

    def process_event(self, event_type: BotPreset, data: dict) -> None:
        """Process an event by executing it on all bot presets.

        Parameters:
            event_type (str): The type of the event.
            data (dict): The data associated with the event.
        """
        for preset in self.bot_presets:
            self.execute_on_event(preset, event_type, data)

    @staticmethod
    def history(interval: str) -> str:
        """Generate a timestamp limit based on the given interval.

        Parameters:
            interval (str or int): The interval to calculate the limit from. It can be a string representing a time interval in
                the format "X:Y" (where X is a number and Y is a unit of time) or an integer representing the number of minutes.

        Returns:
            (str): The timestamp limit in the format "%d.%m.%Y - %H:%M".
        """
        one_minute = 60

        if interval[0].isdigit() and ":" in interval:
            limit = datetime.datetime.now(TZ) - datetime.timedelta(days=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        elif interval[0].isalpha():
            limit = datetime.datetime.now(TZ) - datetime.timedelta(weeks=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        elif int(interval) > one_minute:
            hours = int(interval) // one_minute
            minutes = int(interval) - hours * one_minute
            limit = datetime.datetime.now(TZ) - datetime.timedelta(days=0, hours=hours, minutes=minutes)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        else:
            limit = datetime.datetime.now(TZ) - datetime.timedelta(days=0, hours=0, minutes=int(interval))
            limit = limit.strftime("%d.%m.%Y - %H:%M")

        return limit

    def initialize(self) -> None:
        """Initialize the bot by retrieving bot presets and scheduling jobs based on the preset intervals."""
        logger.debug(f"{self.name}: Awaiting initialization of CORE (timeout: 20s)")
        time.sleep(20)  # wait for the CORE
        response, code = CoreApi.get_bots_presets(self.bot_type)
        if code != HTTPStatus.OK and response is None:
            logger.error(f"Bots presets not received, Code: {code}{', response: ' + str(response) if response is not None else ''}")
            return

        preset_schema = bot_preset.BotPresetSchemaBase(many=True)
        self.bot_presets = preset_schema.load(response)
        logger.debug(f"{self.name}: {len(self.bot_presets)} presets loaded")

        for preset in self.bot_presets:
            preset.last_error_message = None
            preset.log_prefix = f"{self.name} '{preset.name}'"
            preset.logger = create_logger(log_prefix=preset.log_prefix)
            preset.logger.stored_message_levels = ["error", "exception", "warning", "critical"]
            interval = preset.param_key_values["REFRESH_INTERVAL"]
            # do not schedule if no interval is set
            if interval in {"", "0"}:
                preset.logger.info("Disabled")
                continue

            self.run_preset(preset)

            if interval:
                if interval[0].isdigit() and ":" in interval:
                    preset.scheduler_job = SchedulerManager.schedule_job_every_day(interval, self.run_preset, preset.name, preset)

                elif interval[0].isalpha():
                    interval = interval.split(",")
                    day = interval[0].strip()
                    at = interval[1].strip()
                    if day == "Monday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_monday(at, self.run_preset, preset.name, preset)
                    elif day == "Tuesday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_tuesday(at, self.run_preset, preset.name, preset)
                    elif day == "Wednesday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_wednesday(at, self.run_preset, preset.name, preset)
                    elif day == "Thursday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_thursday(at, self.run_preset, preset.name, preset)
                    elif day == "Friday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_friday(at, self.run_preset, preset.name, preset)
                    elif day == "Saturday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_saturday(at, self.run_preset, preset.name, preset)
                    elif day == "Sunday":
                        preset.scheduler_job = SchedulerManager.schedule_job_on_sunday(at, self.run_preset, preset.name, preset)
                else:
                    preset.scheduler_job = SchedulerManager.schedule_job_minutes(int(interval), self.run_preset, preset.name, preset)

    def run_preset(self, preset: BotPreset) -> None:
        """Run the bot on the given preset.

        Parameters:
            preset: The preset to run.
        """
        runner = self.__class__()  # get right type of bot
        runner.preset = preset
        preset.logger.info("Start")
        # self.update_last_attempt(preset)
        runner.execute()
        preset.logger.info("End")
        # self.update_last_error_message(preset)
