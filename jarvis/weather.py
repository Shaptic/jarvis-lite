import os.path
import threading
import math

import csv
import json
import datetime
import ipaddress
import urllib.parse

from typing import *

import requests
import openmeteo_requests
import requests_cache
from   retry_requests import retry
import numpy as np

from .env   import ENV
from .log   import L
from .tasks import *

from . import prompts
from . import chatbot
from . import ip


class WeatherTask(Task):
    URL = "https://api.open-meteo.com/v1/forecast"
    SCHEMA = (
        ["request", "location", "when?"],
        [str, str, str]
    )

    def __init__(self):
        super().__init__()
        cache = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache, retries=5, backoff_factor=0.2)
        self.weather = openmeteo_requests.Client(session=retry_session)
        L.info("Initialized WeatherTask module ...")

    def prepare(self, task_details):
        super().prepare(task_details)
        L.debug(f"WeatherTask module received task: {task_details}")

        lat, long, tz = self._geocode(task_details['location'])
        self.params = {
            "latitude": lat,
            "longitude": long,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": tz,
	        "forecast_days": 14,
            "hourly": ["temperature_2m", "precipitation_probability", "rain", "snowfall", "wind_speed_10m"],
        }
        return self

    def execute(self) -> List[str]:
        """ Returns the weather analysis on the given parameters.
        """
        L.info("WeatherTask module executing task at (%.4f, %.4f) ...",
            self.params['latitude'], self.params['longitude'])
        response = self.weather.weather_api(self.URL, params=self.params)[0]

        # Note: the order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hr_temp = hourly.Variables(0).ValuesAsNumpy()
        hr_chance = hourly.Variables(1).ValuesAsNumpy()
        hr_rain = hourly.Variables(2).ValuesAsNumpy()
        hr_snow = hourly.Variables(3).ValuesAsNumpy()
        hr_wind = hourly.Variables(4).ValuesAsNumpy()

        hours = 0
        when = self.task.get('when', None)
        if when:
            now = datetime.datetime.now()
            relative = datetime.datetime.fromisoformat(when).replace(year=now.year, tzinfo=None)
            diff = relative - now
            hours = min(hr_temp.shape[0]-1, diff.days * 24 + diff.seconds // 3600)

        all_weather = map(
            lambda x: x[hours:hours+8],
            (hr_temp, hr_chance, hr_rain, hr_snow, hr_wind)
        )
        conditions = []

        for i, (temp, chance, rain, snow, wind) in enumerate(zip(*all_weather)):
            t = relative + datetime.timedelta(hours=i)
            s = f"""
at {t.strftime('%I%p').lower().lstrip('0')}:
    {temp:.1f}°F with a {chance if chance != np.nan else 0:.0f}% of precipitation
    ({rain:.1f}in of rain, {snow:.1f}in of snow)
    and {wind:.1f}mph winds"""
            conditions.append(s.replace('\n', '').strip())
            L.debug(s.capitalize().replace('\n', ' '))

        return conditions

    def _geocode(self, location):
        L.debug(f"WeatherTask module locating user ...")

        response = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search?name=' +
            urllib.parse.quote_plus(location)
        )
        if response.status_code != 200:
            raise response

        final = None
        options = response.json()['results']
        country = self.task.get('country_code', 'US').upper()
        for result in options:
            if result['country_code'].upper() == country:
                final = result
                break
        else:
            final = options[0]

        L.debug(f"WeatherTask module located user: {final['name']}")
        return final["latitude"], final["longitude"], final["timezone"]


class WeatherBot:
    """
    """
    PROMPT = prompts.weather

    def __init__(self):
        self.ipdb = ip.IPLookupDB()
        self.thread = threading.Thread(target=self.ipdb.load)
        self.thread.start()

        self._bot = None
        self._weather_bot = chatbot.Chatbot(
            ENV.get('openai'),
            system="You are a bot that summarizes weather conditions in a simple way.",
            response_format="text",
        )
        self._weather_bot.add_injection(
            suffix="""First, give a single-sentence description of the coming
weather. Then, give a short and concise summary of these conditions in a
simple way, generally using descriptive words for the weather rather than
numbers, as well as the appropriate relative time from their original request.
Recommend an outfit for if the user goes outside."""
        )

    @property
    def bot(self):
        if self._bot is None:
            L.warn("Waiting on IP database to load ...")
            self.thread.join()
            self._bot = chatbot.Chatbot(
                ENV.get('openai'),
                system=f"{self.PROMPT} {self.ipdb.get_city()}.",
                response_format="json_object",
            )
        return self._bot

    def run(self, command):
        """ Given the `command` request, returns a weather analysis and an
        outfit recommendation.
        """
        now = datetime.datetime.now()
        current_date = now.strftime("%A, %m/%d/%Y")
        current_time = now.strftime("%I:%M %p")

        task = json.loads(self.bot.prompt(
            f"It is currently {current_time} on {current_date}.\n{command}"
        ))
        task['request'] = command.strip()

        conditions = WeatherTask().prepare(task).execute()
        reply = self._weather_bot.prompt(
            f"The user originally made the following request:\n> {command}\n"
            "Here are the weather conditions over 8 hours on the day the "
            "user requested:\n" + '\n'.join(conditions) + "\n"
        )

        L.debug(f"WeatherBot module received reply: {reply}")
        return reply
