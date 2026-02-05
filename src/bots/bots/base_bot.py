"""BaseBot class represents the base abstract type for all bots."""

import datetime
import time

from remote.core_api import CoreApi

from shared import time_manager
from shared.log_manager import create_logger, logger
from shared.schema import bot, bot_preset


class BaseBot:
    """BaseBot class represents the base abstract type for all bots.

    Attributes:
        type (str): The type of the bot.
        name (str): The name of the bot.
        description (str): The description of the bot.
        parameters (list): The list of parameters for the bot.
    """

    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"
    parameters = []

    def __init__(self):
        """Initialize the BaseBot class."""
        self.bot_presets = []

    def get_info(self):
        """Return the information of the bot.

        Returns:
            (dict): The information of the bot.
        """
        info_schema = bot.BotSchema()
        return info_schema.dump(self)

    def process_event(self, event_type, data):
        """Process an event by executing it on all bot presets.

        Parameters:
            event_type (str): The type of the event.
            data (Any): The data associated with the event.
        """
        for preset in self.bot_presets:
            self.execute_on_event(preset, event_type, data)

    @staticmethod
    def history(interval):
        """Generate a timestamp limit based on the given interval.

        Parameters:
            interval (str or int): The interval to calculate the limit from. It can be a string representing a time interval in
                the format "X:Y" (where X is a number and Y is a unit of time) or an integer representing the number of minutes.

        Returns:
            (str): The timestamp limit in the format "%d.%m.%Y - %H:%M".
        """
        if interval[0].isdigit() and ":" in interval:
            limit = datetime.datetime.now() - datetime.timedelta(days=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        elif interval[0].isalpha():
            limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        elif int(interval) > 60:
            hours = int(interval) // 60
            minutes = int(interval) - hours * 60
            limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        else:
            limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))
            limit = limit.strftime("%d.%m.%Y - %H:%M")

        return limit

    def initialize(self):
        """Initialize the bot by retrieving bot presets and scheduling jobs based on the preset intervals."""
        logger.debug(f"{self.name}: Awaiting initialization of CORE (timeout: 20s)")
        time.sleep(20)  # wait for the CORE
        time_manager.cancel_all_jobs()
        response, code = CoreApi.get_bots_presets(self.type)
        if code == 200 and response is not None:
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
                if interval == "" or interval == "0":
                    preset.logger.info("Disabled")
                    continue

                self.run_preset(preset)

                if interval:
                    if interval[0].isdigit() and ":" in interval:
                        preset.logger.debug(f"Scheduling for {interval} daily")
                        preset.scheduler_job = time_manager.schedule_job_every_day(interval, self.run_preset, preset)
                    elif interval[0].isalpha():
                        interval = interval.split(",")
                        day = interval[0].strip()
                        at = interval[1].strip()
                        preset.logger.debug(f"Scheduling for {day} {at}")
                        if day == "Monday":
                            preset.scheduler_job = time_manager.schedule_job_on_monday(at, self.run_preset, preset)
                        elif day == "Tuesday":
                            preset.scheduler_job = time_manager.schedule_job_on_tuesday(at, self.run_preset, preset)
                        elif day == "Wednesday":
                            preset.scheduler_job = time_manager.schedule_job_on_wednesday(at, self.run_preset, preset)
                        elif day == "Thursday":
                            preset.scheduler_job = time_manager.schedule_job_on_thursday(at, self.run_preset, preset)
                        elif day == "Friday":
                            preset.scheduler_job = time_manager.schedule_job_on_friday(at, self.run_preset, preset)
                        elif day == "Saturday":
                            preset.scheduler_job = time_manager.schedule_job_on_saturday(at, self.run_preset, preset)
                        elif day == "Sunday":
                            preset.scheduler_job = time_manager.schedule_job_on_sunday(at, self.run_preset, preset)
                    else:
                        preset.scheduler_job = time_manager.schedule_job_minutes(int(interval), self.run_preset, preset)
                        preset.logger.debug(f"Scheduling for {preset.scheduler_job.next_run} (in {interval} minutes)")

        else:
            logger.error(f"Bots presets not received, Code: {code}{', response: ' + str(response) if response is not None else ''}")

    def run_preset(self, preset) -> None:
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
