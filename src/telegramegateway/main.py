import os
import logging
from contextlib import asynccontextmanager, AsyncExitStack

from dotenv import load_dotenv

# Load local environment variables before importing application modules.
load_dotenv()

from fastapi import FastAPI

from telegramegateway.routes.telegram import router as telegram_router
from telegramegateway.services.transcription import create_transcription_client
from telegramegateway.services.telegram import (
    get_me,
    set_webhook,
    get_webhook_info,
    initialize_telegram_client,
    close_telegram_client,
)
from agent.utils.workflow import build_workflow
from agent.utils.nami.workflow import build_nami
import httpx

from telegramegateway.agent.utils.robin.workflow import build_robin
from telegramegateway.agent.startup.mcp_robin import initialize_mcp_robin
from telegramegateway.agent.utils.config import NEON_DATABASE_URL
import ngrok
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# from livekit.agents import AgentSession
# from livekit.plugins import langchain
# #langchain.LLMAdapter(graph=create_graph(), stream_mode=["messages", "custom"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)




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
        try:
            # 1. Initialize transcription client
            logger.info("Initializing transcription client...")

            app.state.transcription_client = create_transcription_client()

            # Register cleanup immediately, including if later startup steps fail.
            stack.push_async_callback(app.state.transcription_client.close)

            logger.info("Transcription client initialized.")

            # 2. Initialize MCP
            logger.info("Initializing MCP Robin...")
            mcp_robin = await initialize_mcp_robin()

            logger.info("MCP Robin initialized.")

            # 3. Initialize PostgreSQL checkpointer
            if not NEON_DATABASE_URL:
                raise RuntimeError("NEON_DATABASE_URL is missing.")

            langgraph_db_url = NEON_DATABASE_URL.replace(
                "postgresql+psycopg://",
                "postgresql://",
            )

            logger.info("Connecting to PostgreSQL...")

            saver = await stack.enter_async_context(
                AsyncPostgresSaver.from_conn_string(langgraph_db_url)
            )

            await saver.setup()

            logger.info("PostgreSQL checkpointer initialized.")

            # 4. Build LangGraph workflow
            logger.info("Building Robin workflow...")

            nami = build_nami()

            robin = build_robin(mcp_robin["tool_node"])
            workflow = build_workflow(robin, nami)
            app.state.agent_app = workflow.compile(
                checkpointer=saver
            )

            logger.info("LangGraph agent initialized.")

            # 5. Connect to Telegram
            logger.info("Connecting to Telegram...")
# Initialize Telegram HTTP client
            logger.info("Initializing Telegram HTTP client...")

            await initialize_telegram_client()
            stack.push_async_callback(close_telegram_client)

            logger.info("Telegram HTTP client initialized.")

            # Connect to Telegram
            bot = await get_me()

            logger.info(
                "Connected to Telegram: @%s (ID: %s)",
                bot["username"],
                bot["id"],
            )

            webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
            webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")

            if not webhook_url:
                raise RuntimeError("TELEGRAM_WEBHOOK_URL is missing.")

            await set_webhook(
                webhook_url=webhook_url,
                secret_token=webhook_secret,
            )

            webhook_info = await get_webhook_info()

            if webhook_info.get("url") != webhook_url:
                raise RuntimeError(
                    "Telegram webhook registration could not be verified."
                )

            logger.info("Telegram webhook active: %s", webhook_url)
            logger.info("MaintiDoc is ready.")

            yield

        except Exception:
            logger.exception("MaintiDoc startup or runtime failed.")
            raise

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