import openai

from env import ENV

import prompts
import chatbot
import weather
import lists


class Orchestra:
    """ In charge of manipulating state and combining tasks.
    """
    PROMPT = prompts.orchestra

    def __init__(self):
        self.client = openai.OpenAI(api_key=ENV.get('openai'))
        self.bot = chatbot.Chatbot(
            ENV.get('openai'),
            system=self.PROMPT.strip(),
            response_format="json_object",
        )
        self.weather = weather.WeatherBot()
        self.lists = lists.ListManagementBot()

    def transcribe(self, f) -> str:
        transcript = self.client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcript.text
