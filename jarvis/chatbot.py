from typing import *

import pprint
import json

import openai


DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
GPT_MODEL = "gpt-4-1106-preview"


def build_system_prompt(*args):
    return {"role": "system", "content": ' '.join(args).strip()}

def build_user_prompt(*args):
    return {"role": "user", "content": ' '.join(args).strip()}

def build_bot_reply(*args):
    return {"role": "assistant", "content": ' '.join(args)}

def best_effort_json(raw_text: str, default: dict={}) -> dict:
    """ Given an arbitrary piece of text, this makes a best effort to find
    parseable JSON within it. This helps when ChatGPT breaks your rules around
    only responding with JSON and includes some preamble bullshit.
    """
    s = raw_text.find('{')
    e = raw_text.rfind('}')

    if s == -1 or e == -1 or e < s:
        return default

    return json.loads(raw_text[s:e+1])


class Chatbot:
    """ A wrapper around OpenAI's ChatGPT API.

    This wrapper adds conversation history, convenience methods around building
    a conversation, tracks bot responses, and presents errors in a friendly way.
    """

    def __init__(self,
        API_KEY,
        system: str=DEFAULT_SYSTEM_PROMPT,
        history_file: Optional[List[str]]=None,
        response_format: Optional[
            openai.types.chat.completion_create_params.ResponseFormat
        ]='text',
        debug: bool=False,
    ):
        self.suffix_injections = []
        self.prefix_injections = []
        self.history = [
            build_system_prompt(system),
        ]
        self.debug = debug
        self.response = response_format

        self.history_file = history_file
        if history_file is not None:
            self.history.extend(json.load(open(history_file, "rt")))

        self.client = openai.OpenAI(api_key=API_KEY)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        if self.history_file:
            with open(self.history_file, "wt") as hf:
                json.dump(hf, self.history)

    def add_preamble(self, *prompts):
        self.history.extend(prompts)
        return self

    def add_injection(self, prefix: Optional[str]=None, suffix: Optional[str]=None):
        if prefix is None and suffix is None:
            raise ValueError(f"at least one of 'prefix' or 'suffix' needs to be defined")

        if prefix: self.prefix_injections.append(prefix)
        if suffix: self.suffix_injections.append(suffix)
        return self

    def prompt(self, text: str):
        if text:
            self.history.append(
                build_user_prompt(
                    '.\n'.join(self.prefix_injections),
                    f"{text}.",
                    '.\n'.join(self.suffix_injections)))

        return self._send()

    def _send(self):
        if self.debug:
            pprint.pprint(self.history)

        bot = self.client.chat.completions.create(
            model=GPT_MODEL,
            presence_penalty=1,
            # frequency_penalty=1.05,
            # temperature=1.25,
            messages=self.history,
            response_format={"type": self.response},
            n=1,
        )

        if len(bot.choices) > 1:
            print("TODO: more than one response is unsupported")
            breakpoint()

        for reply in bot.choices:
            if reply.finish_reason == "length":
                print("WARNING: Partial reply returned due to length cap.")

            if reply.finish_reason == "stop" or reply.finish_reason == "length":
                content = reply.message.content
                if self.debug: pprint.pprint(content)
                self.history.append(build_bot_reply(content))
                return content

            else:
                pprint.pprint(reply)
                print("TODO: unsupported 'finish_reason':", reply.finish_reason)
                breakpoint()
