"""BaseBot class represents the base abstract type for all bots."""

import datetime
import time
from managers import time_manager
from managers.log_manager import logger
from shared.schema import bot, bot_preset
from remote.core_api import CoreApi


class BaseBot:
    """BaseBot class represents the base abstract type for all bots.

    Attributes:
        type (str): The type of the bot.
        name (str): The name of the bot.
        description (str): The description of the bot.
        parameters (list): The list of parameters for the bot.
    Methods:
        __init__(): Initializes a new instance of the BaseBot class.
        get_info(): Gets the information of the bot.
        execute(source): Executes the bot's task.
        execute_on_event(preset, event_type, data): Executes the bot's task based on an event.
        process_event(event_type, data): Processes an event and executes the bot's task for each preset.
        history(interval): Returns the history limit based on the given interval.
        initialize(): Initializes the bot and schedules its execution based on the presets.
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
        else:
            if int(interval) > 60:
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
        time.sleep(20)  # wait for the CORE
        response, code = CoreApi.get_bots_presets(self.type)
        if code == 200 and response is not None:
            preset_schema = bot_preset.BotPresetSchemaBase(many=True)
            self.bot_presets = preset_schema.load(response)
            logger.debug(f"{self.name}: {len(self.bot_presets)} presets loaded")

            for preset in self.bot_presets:
                interval = preset.parameter_values["REFRESH_INTERVAL"]
                # do not schedule if no interval is set
                if interval == "" or interval == "0":
                    logger.debug(f"scheduling '{preset.name}' disabled")
                    continue

                self.execute(preset)

                if interval:
                    if interval[0].isdigit() and ":" in interval:
                        logger.debug(f"scheduling '{preset.name}' at: {interval}")
                        time_manager.schedule_job_every_day(interval, self.execute, preset)
                    elif interval[0].isalpha():
                        interval = interval.split(",")
                        day = interval[0].strip()
                        at = interval[1].strip()
                        logger.debug(f"scheduling '{preset.name}' at: {day} {at}")
                        if day == "Monday":
                            time_manager.schedule_job_on_monday(at, self.execute, preset)
                        elif day == "Tuesday":
                            time_manager.schedule_job_on_tuesday(at, self.execute, preset)
                        elif day == "Wednesday":
                            time_manager.schedule_job_on_wednesday(at, self.execute, preset)
                        elif day == "Thursday":
                            time_manager.schedule_job_on_thursday(at, self.execute, preset)
                        elif day == "Friday":
                            time_manager.schedule_job_on_friday(at, self.execute, preset)
                        elif day == "Saturday":
                            time_manager.schedule_job_on_saturday(at, self.execute, preset)
                        else:
                            time_manager.schedule_job_on_sunday(at, self.execute, preset)
                    else:
                        logger.debug(f"scheduling '{preset.name}' for {interval}")
                        time_manager.schedule_job_minutes(int(interval), self.execute, preset)

        else:
            logger.error(f"Bots presets not received, Code: {code}" f"{', response: ' + str(response) if response is not None else ''}")
