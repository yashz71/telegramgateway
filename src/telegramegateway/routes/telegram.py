
import os
import logging

from fastapi import APIRouter, Request, HTTPException

from telegramegateway.services.telegram import (
    send_text_message,
    download_file,
)

from telegramegateway.services.telegram_handler import handle_telegram_message

router = APIRouter(
    prefix="/webhook/telegram",
    tags=["Telegram"],
)

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")


@router.get("")
async def telegram_health():
    return {
        "status": "active",
        "service": "Telegram webhook",
    }


@router.post("")
async def receive_telegram_update(request: Request):
    """Receive Telegram webhook updates."""

    # Verify the webhook secret.
    if WEBHOOK_SECRET:
        received_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )

        if received_secret != WEBHOOK_SECRET:
            raise HTTPException(
                status_code=403,
                detail="Invalid Telegram webhook secret",
            )

    update = await request.json()

    update_id = update.get("update_id")

    if update_id is None:
        raise HTTPException(
            status_code=400,
            detail="Missing update_id",
        )

    message = update.get("message")

    # Ignore unsupported update types for now.
    if not message:
        return {"ok": True}

    try:
        agent_app = request.app.state.agent_app

        await handle_telegram_message(
            message=message,
            agent_app=agent_app,
            transcription_client=request.app.state.transcription_client,
            #whisper_pipe=request.app.state.whisper_pipe,
        )
    except Exception:
        logger.exception(
            "Failed to process Telegram update %s",
            update_id,
        )

        # Telegram may retry unsuccessful webhook deliveries.
        raise HTTPException(
            status_code=500,
            detail="Message processing failed",
        )

    return {"ok": True}
