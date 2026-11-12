
import base64
import logging
import mimetypes
from pathlib import Path
from uuid import uuid4
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from langchain_core.messages import HumanMessage

from telegramegateway.services.telegram import download_file, send_text_message
from telegramegateway.services.transcription import transcribe_audio
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/telegram")



def fresh_turn_state(user_message: HumanMessage) -> dict:
    return {
        "messages": [user_message],
        "plan": None,
        "parallel": True,
        "reasoning": None,
        "supervisor_instruction": None,
        "accounting_answer": None,
        "tax_answer": None,
        "general_answer": None,
        "download_url": None,
    }


def build_multimodal_message(
    message_text: str,
    photo_path: str | None,
) -> HumanMessage:
    """
    Build one LangChain HumanMessage containing text, an image,
    or both.

    The image is encoded as a data URL so a vision-capable
    chat model can process it.
    """
    content = []

    if message_text.strip():
        content.append({
            "type": "text",
            "text": message_text.strip(),
        })

    if photo_path:
        image_file = Path(photo_path)

        if not image_file.is_file():
            raise FileNotFoundError(
                f"Downloaded Telegram image not found: {image_file}"
            )

        mime_type, _ = mimetypes.guess_type(image_file.name)
        mime_type = mime_type or "image/jpeg"

        with image_file.open("rb") as image:
            encoded_image = base64.b64encode(
                image.read()
            ).decode("utf-8")

        image_data_url = (
            f"data:{mime_type};base64,{encoded_image}"
        )

        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_data_url,
            },
        })

    return HumanMessage(content=content)


async def run_maintidoc_agent(
    agent_app,
    chat_id: int,
    message_text: str,
    photo_path: str | None,
) -> str:
    """
    Invoke the existing MaintiDoc LangGraph application.

    Each Telegram chat has its own persistent LangGraph thread.
    """
    thread_id = f"telegram:{chat_id}"
    user_message = build_multimodal_message(
        message_text=message_text,
        photo_path=photo_path,
    )

    
    input_state = fresh_turn_state(user_message) 
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = await agent_app.ainvoke(
        input_state,
        config=config,
    )

    messages = result.get("messages", [])

    if not messages:
        return "I couldn't generate a response. Please try again."

    final_message = messages[-1]

    # Most LangGraph chat workflows return an AIMessage here.
    answer = getattr(final_message, "content", "")

    if isinstance(answer, str):
        return answer.strip()

    # Handle structured content responses where possible.
    if isinstance(answer, list):
        text_parts = [
            block["text"]
            for block in answer
            if isinstance(block, dict)
            and block.get("type") == "text"
            and block.get("text")
        ]
        return "\n".join(text_parts).strip()

    return str(answer)


async def handle_telegram_message(
    message: dict,
    agent_app,
    transcription_client
) -> None:
    """Normalize and process an incoming Telegram message."""

    chat = message.get("chat", {})
    sender = message.get("from", {})

    chat_id = chat.get("id")
    sender_id = sender.get("id")

    if chat_id is None or sender_id is None:
        logger.warning(
            "Ignoring Telegram message without chat or sender ID"
        )
        return

    message_id = message.get("message_id")

    # Text or caption.
    message_text = (
        message.get("text")
        or message.get("caption")
        or ""
    )

    photo_path = None
    audio_path = None

    photos = message.get("photo", [])

    # Telegram can send either voice messages or audio files.
    voice = message.get("voice")
    audio = message.get("audio")

    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # -----------------------------------------
        # 1. Handle photos
        # -----------------------------------------
        if photos:
            largest_photo = photos[-1]
            file_id = largest_photo["file_id"]

            destination = UPLOAD_DIR / f"{uuid4().hex}.jpg"

            photo_path = str(
                await download_file(file_id, destination)
            )

        # -----------------------------------------
        # 2. Handle audio / voice messages
        # -----------------------------------------
        audio_file = voice or audio

        if audio_file:
            file_id = audio_file["file_id"]

            # Voice messages are normally OGG/Opus.
            # Audio files may be MP3, M4A, etc.
            if voice:
                extension = ".ogg"
            else:
                extension = Path(
                    audio_file.get("file_name", "audio.mp3")
                ).suffix or ".mp3"

            destination = (
                UPLOAD_DIR / f"{uuid4().hex}{extension}"
            )

            audio_path = str(
                await download_file(file_id, destination)
            )

            logger.info(
                "Transcribing Telegram audio: chat=%s file=%s",
                chat_id,
                audio_path,
            )

            # Transcribe without blocking the async event loop.
            transcription = await transcribe_audio(
                transcription_client=transcription_client,
                #whisper_pipe=whisper_pipe,
                audio_path=audio_path,
            )
            if not transcription:
                await send_text_message(
                    chat_id,
                    "I couldn't understand the audio. "
                    "Please try recording it again.",
                )
                return

            logger.info(
                "Audio transcription completed: chat=%s text=%s",
                chat_id,
                transcription,
            )

            # Combine caption and transcription if both exist.
            if message_text.strip():
                message_text = (
                    f"{message_text.strip()}\n\n"
                    f"Audio transcription: {transcription}"
                )
            else:
                message_text = transcription

        # -----------------------------------------
        # 3. Validate incoming message
        # -----------------------------------------
        if not message_text.strip() and not photo_path:
            await send_text_message(
                chat_id,
                "Please send a text message, photo, "
                "voice message, or audio file.",
            )
            return

        # -----------------------------------------
        # 4. Log message type
        # -----------------------------------------
        message_type = (
            "photo+audio" if photo_path and audio_path
            else "photo+text" if photo_path and message_text
            else "photo" if photo_path
            else "audio" if audio_path
            else "text"
        )

        logger.info(
            "Processing Telegram message: chat=%s sender=%s "
            "message_id=%s type=%s",
            chat_id,
            sender_id,
            message_id,
            message_type,
        )

        # -----------------------------------------
        # 5. Invoke MaintiDoc agent
        # -----------------------------------------
        response = await run_maintidoc_agent(
            agent_app=agent_app,
            chat_id=chat_id,
            message_text=message_text,
            photo_path=photo_path,
        )

        if response:
            await send_text_message(chat_id, response)

    except Exception:
        logger.exception(
            "MaintiDoc processing failed for chat %s",
            chat_id,
        )

        await send_text_message(
            chat_id,
            "Sorry, I encountered an error while processing "
            "your request. Please try again.",
        )

    finally:
        # -----------------------------------------
        # 6. Clean up temporary files
        # -----------------------------------------
        if photo_path:
            Path(photo_path).unlink(missing_ok=True)

        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
