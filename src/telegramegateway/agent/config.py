import os
from dotenv import load_dotenv

# This loads the variables from .env into the standard os.environ dictionary
load_dotenv(override=True)

# Extract variables safely
base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")
mcp_server_url_robin = os.getenv("MCP_SERVER_URL_ROBIN")

NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "wealth_management_2026")

# Fail-safe: Stop the server immediately if critical keys are missing
if not NEON_DATABASE_URL:
    raise ValueError("Critical configuration is missing! Check your .env file.")