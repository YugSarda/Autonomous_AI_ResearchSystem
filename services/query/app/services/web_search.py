import os
import requests
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_web(query):
    url = "https://api.tavily.com/search"

    response = requests.post(url, json={
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced"
    })

    results = response.json().get("results", [])

    return [r["content"] for r in results[:5]]
