from langchain_openai import ChatOpenAI
from agent.utils.config import base_url, api_key

model = ChatOpenAI(
    model="gpt-4.1-nano",
    base_url=base_url,
    api_key=api_key,
    temperature=0,
    stream_usage=True,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

