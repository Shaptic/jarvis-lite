# JarvisLite: The simplest personal assistant.

JarvisLite is a proof-of-concept that demonstrates how to build a very simple personal assistant with minimal code using a combination of OpenAI's APIs.

## Features

Besides just conversing with a chatbot, it supports two more features that a personal assistant would be capable of:
 - checking the weather
 - manipulating categories of lists (like a TODO or grocery list)

Each of these has full natural language support: for example, you can ask whether (heh) or not you need to wear a rain jacket tomorrow.

## Architecture

The architecture is relatively simple:

 1. A simple state machine transitions from listening to your voice to parsing your commands to executing the requested task.
 2. The transcription is interpreted as a command, which is then passed along to be interpreted as a task-specific structure.
 3. The task is then executed and the result is spoken.

Visually,

    speak -> Whisper -> GPT-4 -> 
      a TypeScript interface distinguishing a command -> [
        if weather:
          fetch weather at given location and time ->
            GPT4 ->
              a nice description of weather conditions
        elif lists:
          GPT4 -> how are we manipulating the list? -> do that
      ] -> speak result

## Installation

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

If you get an error installing [`openwakeword`](https://github.com/dscripka/openWakeWord), try dropping the line and installing it directly from the GitHub repository, instead:

```bash
pip install git+https://github.com/dscripka/openWakeWord.git
```

You will need an OpenAI API key. Once you have it, running the assistant is as simple as:

```bash
OPENAI_KEY="your_api_key" python -m jarvis
```

The activation phrase is "Hey Jarvis".
