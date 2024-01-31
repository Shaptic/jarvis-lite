# JarvisLite: A simple personal assistant backed by OpenAI.

JarvisLite is a proof-of-concept that demonstrates how to build a very simple personal assistant with minimal code using a combination of OpenAI's APIs.

The architecture is relatively simple:

 1. A simple state machine transitions from listening to your voice to parsing your commands to executing the requested task.
 2. The transcription is interpreted as a command, which is then passed along to be interpreted as a task-specific structure.
 3. The task is then executed and the result is spoken.

Visually,

    your voice -> transcription (Whisper model) -> 
    text LLM (GPT4 model) -> a TypeScript interface distinguishing a command ->
    execution of the command -> [
      if weather:
        fetch weather at given location and time -> text LLM -> 
        a nice description of weather conditions

      elif lists:
        text LLM -> interpret what way we are manipulating the list ->
        execute the action (modify, read off, etc.)
    ] -> speak result

## Features

Besides just conversing with a chatbot, it supports two more features that a personal assistant would be capable of:
 - checking the weather
 - manipulating categories of lists (like a TODO or grocery list)

Each of these has full natural language support: for example, you can ask whether (heh) or not you need to wear a rain jacket tomorrow.

## Installation

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

If you get an error installing `openwakeword`, try dropping the line and installing it directly from the GitHub repository, instead:

```bash
pip install git+https://github.com/dscripka/openWakeWord.git
```

You will need an OpenAI API key. Once you have it, running the assistant is as simple as:

```bash
cd src/ && OPENAI_KEY="your_api_key" python main.py
```

The activation phrase is "Hey Jarvis".
