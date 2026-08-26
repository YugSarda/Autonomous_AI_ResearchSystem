import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion:8001")
QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query:8002")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory:8003")

# Rate limiting defaults
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds