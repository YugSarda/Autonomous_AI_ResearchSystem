import os
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# LLM BACKEND (Gemini) - replaces Ollama/Mistral
# =========================================================
# Old Ollama config (kept for reference, no longer used):
# OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
# MODEL_NAME = os.getenv("MODEL_NAME", "mistral")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "data/vector_store")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion:8001")
QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query:8002")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory:8003")