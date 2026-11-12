# import asyncio
# from transformers import pipeline


# def load_whisper():
#     return pipeline(
#         "automatic-speech-recognition",
#         model="openai/whisper-base",
#     )


# async def transcribe_audio(
#     whisper_pipe,
#     audio_path: str,
# ) -> str:
#     result = await asyncio.to_thread(
#         whisper_pipe,
#         audio_path,
#             generate_kwargs={
#                 "language": "english",
#                 "task": "transcribe",
#             },
        
        
#     )

#     return result.get("text", "").strip()

import os
from pathlib import Path
from openai import AsyncAzureOpenAI


def create_transcription_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/"),
        api_version="2025-03-01-preview",
    )

async def transcribe_audio(
    transcription_client: AsyncAzureOpenAI,
    audio_path: str,
) -> str:
    path = Path(audio_path)

    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")

    content_types = {
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }

    content_type = content_types.get(
        path.suffix.lower(),
        "application/octet-stream",
    )

    with path.open("rb") as audio_file:
        result = await transcription_client.audio.transcriptions.create(
            model="gpt-transcribe",
            file=(path.name, audio_file, content_type),
        )

    return result.text.strip()