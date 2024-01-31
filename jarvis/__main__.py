import os
import enum
import json
import pathlib
import datetime
import tempfile
import subprocess
import collections

import pydub            # audio manip
import pydub.playback   # audio playback
import pydub.effects    # misc. sfx
import pyaudio          # mic streaming
import openwakeword
import openwakeword.model

import numpy  as np
from   openai import OpenAI

from . import orchestra
from . import chatbot
from . import tasks

from .env import ENV
from .log import L


BING = pydub.AudioSegment.from_file(os.path.join(ENV.get('data'), 'bing.mp3'))
FORMAT = pyaudio.paInt16
CHUNK = 1280*2
RATE = 16000
CHANNELS = 1

audio = pyaudio.PyAudio()
client = OpenAI(api_key=ENV.get('openai'))


class State(enum.Enum):
    Waiting = 0
    Recording = 1
    Transcribing =2
    Analyzing = 3
    Playing = 4
    Execute = 5
    Done = 6


def tts(text: str, speed=1.2):
    """ Plays the given `text` using OpenAI's text-to-speech API.
    """
    L.debug(f"Jarvis is speaking: '{text}' ...")
    audio_path = tempfile.NamedTemporaryFile(suffix='.mp3').name
    L.debug(f"Saving transcription to {audio_path} ...")

    text = text.replace("'", '"')
    with (
        client.audio.speech
        .with_streaming_response
        .create(
            model="tts-1-hd",
            voice="nova",
            input=text,
            response_format='mp3',
            speed=speed,
        )
    ) as response:
        response.stream_to_file(audio_path)
        seg = pydub.AudioSegment.from_mp3(audio_path)
        pydub.playback.play(seg)

def make_empty_segment():
    return pydub.AudioSegment(
        b'',
        sample_width=audio.get_sample_size(FORMAT),
        frame_rate=RATE,
        channels=1
    )

def main():
    L.info("Booting Jarvis ...")
    # openwakeword.utils.download_models(['hey_jarvis_v0.1'])
    model = openwakeword.model.Model(
        wakeword_models=list(map(
            lambda p: os.path.join(ENV.get('data'), "models", p),
            [
                "hey_jarvis_v0.1.tflite",
            ]
        ))
    )
    mic = audio.open(
        format=FORMAT,
        frames_per_buffer=CHUNK,
        channels=CHANNELS,
        rate=RATE,
        input=True
    )

    state = State.Waiting
    recording = make_empty_segment()
    command = ''
    task = {}

    jarvis = orchestra.Orchestra()

    # For testing: TTS on a prompt response
    task = {
        'type': 'chat',
        'confidence': 1,
        'content': "do you recognize this meme reference? 'hello, i am under the water - please help me'"
        # 'content': "i am a retarded little yapper who hates women",
        #masha you are a yapper and need special ed",
        # 'content': 'Даша, маленькая девочка из небольшой деревни, всегда мечтала о больших приключениях. Однажды, она нашла старую книгу в бабушкиной библиотеке, в которой рассказывалось о волшебном мире за таинственным порталом. Не смогла устоять перед соблазном и решила отправиться в путешествие. Проходя через портал, Даша оказалась в волшебном лесу, где встретила разноцветных сказочных существ. Вместе с новыми друзьями она преодолела множество испытаний и обрела силу, о которой и не мечтала. Вернувшись домой, Даша поняла, что настоящее волшебство – в самом сердце каждого приключения, и что маленькие девочки тоже могут совершать великие подвиги.'
    }
    state = State.Execute
    command = 'can you add cucumbers to my grocery list?'
    task = {
        'type': 'todo',
    }

    pause = 0
    while state != State.Done:
        # L.debug(f"{state} (pause={pause})")
        if state == State.Waiting:
            chunk = np.frombuffer(mic.read(CHUNK), dtype=np.int16)
            prediction = model.predict(chunk)

            for mdl, scores in model.prediction_buffer.items():
                last_score = next(reversed(scores))
                if pause <= 0 and last_score >= 0.75:
                    L.info(f"Wakeword detected (model={mdl}): {last_score:2f}")
                    pydub.playback.play(BING.fade_out(1))
                    state = State.Recording
                    pause = 5
                    break
                elif pause > 0:
                    L.debug(f"Paused wakeword detection: {pause} more iterations")

        elif state == State.Recording:
            L.debug("Recording user voice command ...")
            chunk = mic.read(CHUNK)
            chunk_segment = pydub.AudioSegment(
                chunk,
                sample_width=audio.get_sample_size(FORMAT),
                frame_rate=RATE,
                channels=1,
            )
            recording = recording.append(chunk_segment, crossfade=0)

            if recording.duration_seconds > 5:
                pydub.playback.play(BING.reverse().speedup(3))
                state = State.Transcribing
            #     silence = pydub.silence.detect_silence(
            #         recording,
            #         min_silence_len=1000,
            #         silence_thresh=-16,
            #         seek_step=5
            #     )
            #     print("Silence:", silence)

            #     # We stop recording iff:
            #     #   - there's silence at the end of the detection mechanism
            #     #   - there has been a non-silent gap
            #     if len(silence) >= 2:
            #         last_start, last_end = silence[-1]
            #         if last_end == len(silence) and last_start != 0:
            #             print("silence at the end")
            #     else:
            #         print("no action yet")

        elif state == State.Transcribing:
            L.info("Transcribing user command to text ...")
            with tempfile.NamedTemporaryFile(suffix='.wav', mode='rb') as tf:
                recording.export(tf.name, format='wav')
                tf.seek(0)
                command = jarvis.transcribe(pathlib.Path(tf.name))

            recording = make_empty_segment()
            state = State.Analyzing

        elif state == State.Analyzing:
            L.info(f"Jarvis is analyzing command: '{command}' ...")
            response = jarvis.bot.prompt(command)
            task.clear()
            task.update(json.loads(response))
            state = State.Execute

        elif state == State.Execute:
            L.info(f"Jarvis executing task: {task} (command='{command}')")
            ttype = task["type"].lower()
            if ttype == 'quit':
                state = State.Done
            elif ttype == 'chat':
                tts(task['content'])
                state = State.Waiting
                model.reset()
            else:
                if ttype == 'weather':
                    tts(jarvis.weather.run(command), speed=1.5)
                elif ttype == 'lists':
                    tts(jarvis.lists.run(command), speed=1.5)

                state = State.Waiting
                model.reset()
                task.clear()

        if pause > 0: pause -= 1

try:
    main()
except KeyboardInterrupt:
    L.warning("Jarvis is powering down ...")
