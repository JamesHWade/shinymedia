import os
from pathlib import Path
from typing import Any
import tempfile
import base64
import re

import dotenv
from openai import AsyncOpenAI
from shiny import ui
from pydub import AudioSegment

# Load OpenAI API key from .env file
dotenv.load_dotenv()
if os.environ.get("OPENAI_API_KEY") is None:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = AsyncOpenAI()

def parse_data_uri(data_uri):
    match = re.match(r'data:(.+);base64,(.+)', data_uri)
    if not match:
        raise ValueError("Invalid data URI format")
    mime_type, b64data = match.groups()
    # Add padding if necessary
    padding = len(b64data) % 4
    if padding:
        b64data += '=' * (4 - padding)
    return mime_type, base64.b64decode(b64data)

async def chat(audio_input: str, messages: list[Any], progress: ui.Progress) -> str:
    progress.set(message="Decoding input...", value=0)

    # Parse the data URI
    mime_type, audio_bytes = parse_data_uri(audio_input)

    # Convert WebM to MP3
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as webm_file:
        webm_file.write(audio_bytes)
        webm_file.flush()

        audio = AudioSegment.from_file(webm_file.name, format="webm")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
            audio.export(mp3_file.name, format="mp3")
            mp3_path = mp3_file.name

    # Decode the audio file into text, using OpenAI's `whisper-1` model.
    progress.set(message="Transcribing audio...", value=0.1)
    with open(mp3_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )

    # Clean up temporary files
    os.unlink(webm_file.name)
    os.unlink(mp3_path)

    user_prompt = transcription.text

    # We're ready to talk to the LLM: use the transcribed text as input, and get generated text back.
    messages.append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )

    progress.set(message="Waiting for response...", value=0.2)
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            *messages,
            {
                "role": "system",
                "content": Path("system_prompt.txt").read_text(),
            },
        ],
    )
    response_text = response.choices[0].message.content
    messages.append(response.choices[0].message)

    # Use OpenAI's text-to-speech model to turn the generated text into audio.
    progress.set(message="Synthesizing audio...", value=0.8)
    audio = await client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=response_text or "",
        response_format="mp3",
    )
    response_audio_uri = f"data:audio/mpeg;base64,{base64.b64encode(audio.read()).decode('utf-8')}"
    return response_audio_uri