from langchain_tavily import TavilySearch
import os
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

search_tool = TavilySearch(max_results=2)