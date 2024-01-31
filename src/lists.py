import json
import collections

import chatbot
import prompts

from log   import L
from env   import ENV
from tasks import Task


class ListTask(Task):
    SCHEMA = (
        [ "action", "list", "content?", "more_help?" ],
        [ str, str, str, str ]
    )

    def __init__(self, task_db):
        self.db = task_db

    def prepare(self, task_details):
        super().prepare(task_details)
        return self

    def execute(self):
        action, listname, content, moar = map(
            lambda k: self.task.get(k, None),
            ('action', 'list', 'content', 'more_help')
        )

        if action == 'add':
            self.db[listname].append(content)
            return f"Okay, I've added {content} to your list called '{listname}'."

        elif action == 'remove':
            try:
                self.db[listname].remove(content)
                return f"Okay, I've removed {content} from your list called '{listname}'."
            except:
                return f"The list {listname} has no item called {content}."

        elif action == 'read':
            # which list should we read?
            bot = chatbot.Chatbot(
                ENV.get("openai"),
                system="""You are an interpreter that can turn a structured set
of lists into something that would be a good output for a personal assistant
bot. Respond with a JSON blob following this interface:

interface Output {
    prompt: string;
}""",
                response_format="json_object",
                debug=True
            )
            return json.loads(bot.prompt(
                ("list_database=" + repr(self.db)) if not listname \
                    else f"{listname}=" + repr(self.db[listname])))['prompt']

        elif action == 'custom':
            return self.task


class ListManagementBot:
    """ Creates a structured command from arbitrary text and executes it.
    """
    PROMPT = prompts.todo

    def __init__(self):
        L.info("Jarvis initializing Todo module ...")
        self.bot = chatbot.Chatbot(
            ENV.get('openai'),
            system=self.PROMPT,
            response_format="json_object",
            debug=True
        )

        self.task_db = collections.defaultdict(list)

        L.info("Jarvis initialized Todo module: %d lists, %d total items",
            len(self.task_db),
            sum(map(len, self.task_db.values()))
        )

    def run(self, command):
        prefix = '' if not self.task_db else \
            f"Here are some of the lists that we already know about: {json.dumps(self.task_db)}."

        reply = self.bot.prompt(
            prefix + f"\nThe user asked for this: '{command}'"
        )
        L.debug(reply)
        task = ListTask(self.task_db).prepare(json.loads(reply))
        result = task.execute()
        if isinstance(result, str):
            return result

        reply = self.bot.prompt(result["moar"])
        L.debug(reply)
        return reply