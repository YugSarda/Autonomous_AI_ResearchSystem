from app.core.cache import get_cache, set_cache

MEMORY_KEY = "conversation_memory"


def get_memory():
    return get_cache(MEMORY_KEY) or []


def add_memory(query, answer):
    memory = get_memory()
    memory.append({"query": query, "answer": answer})
    set_cache(MEMORY_KEY, memory[-10:])