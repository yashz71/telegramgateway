
from http.client import HTTPException
import os
import logging
from contextlib import asynccontextmanager, AsyncExitStack
import secrets
from typing import Optional
from pydantic import BaseModel

from dotenv import load_dotenv

# Load environment variables before importing modules that use them.
load_dotenv()

import ngrok
from fastapi import FastAPI, Header

from routes.telegram import router as telegram_router

from services.telegram import (
    get_me,
    set_webhook,
    get_webhook_info,
)


from agent.utils.robin.workflow import build_robin

from agent.startup.mcp_robin import initialize_mcp_robin
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent.utils.config import NEON_DATABASE_URL


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

approved_drafts = {}



 
def connect_ngrok():
    forwarder = ngrok.forward(
        "localhost:8085",
        authtoken_from_env=True,
        domain="among-aged-mammogram.ngrok-free.dev",
    )

    public_url = forwarder.url()
    logger.info("Ngrok tunnel available at: %s", public_url)

    return public_url





@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting MaintiDoc...")

    async with AsyncExitStack() as stack:

        # --------------------------------------------------
        # 1. Initialize MCP servers
        # --------------------------------------------------

       
        mcp_robin = await initialize_mcp_robin()
        # --------------------------------------------------
        # 2. Build the individual agents
        # --------------------------------------------------

        # --------------------------------------------------
        # 3. Initialize persistent PostgreSQL checkpointer
        # --------------------------------------------------

        langgraph_db_url = NEON_DATABASE_URL.replace(
            "postgresql+psycopg://",
            "postgresql://",
        )

        saver = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(
                langgraph_db_url
            )
        )

        await saver.setup()

        # --------------------------------------------------
        # 4. Build and compile the workflow ONCE
        # --------------------------------------------------

        workflow = build_robin(
         mcp_robin["tool_node"]
        )

        agent_app = workflow.compile(
            checkpointer=saver
        )

        app.state.agent_app = agent_app

        logger.info("MaintiDoc LangGraph agent initialized.")

        # --------------------------------------------------
        # 5. Connect to Telegram
        # --------------------------------------------------

        bot = await get_me()

        logger.info(
            "Connected to Telegram: @%s (ID: %s)",
            bot["username"],
            bot["id"],
        )

        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")

        if not webhook_url:
            raise RuntimeError(
                "TELEGRAM_WEBHOOK_URL is missing from .env"
            )

        await set_webhook(
            webhook_url=webhook_url,
            secret_token=webhook_secret,
        )

        webhook_info = await get_webhook_info()

        if webhook_info.get("url") != webhook_url:
            raise RuntimeError(
                "Telegram webhook registration could not be verified."
            )

        logger.info(
            "Telegram webhook active: %s",
            webhook_info["url"],
        )

        logger.info("MaintiDoc is ready.")

        # The checkpointer stays open while FastAPI is running.
        yield

        logger.info("MaintiDoc is shutting down.")


app = FastAPI(
    title="MaintiDoc API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(telegram_router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "MaintiDoc",
    }


if __name__ == "__main__":
    import uvicorn

    # Start the tunnel before the FastAPI server.
    connect_ngrok()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8085,
    )
