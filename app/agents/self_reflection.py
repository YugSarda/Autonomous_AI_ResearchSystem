from app.core.ollama_client import generate

def reflect(answer):
    prompt = f"""
What is missing?
Improve answer:

{answer}
"""
    return generate(prompt)