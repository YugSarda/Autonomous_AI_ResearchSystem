from app.core.ollama_client import generate
import re


def critique(answer):

    print("🧪 Critic Agent Running...")

    prompt = f"""
Evaluate this answer.

Return STRICTLY in this format:

Score: <number>

Missing Parts:
...

Hallucination Risk:
...

Answer:
{answer}
"""

    response = generate(prompt)

    print("📄 Critic raw response:")
    print(response)

    score_match = re.search(
        r"Score\s*:\s*(\d+)",
        response,
        re.IGNORECASE
    )

    if score_match:

        score = int(score_match.group(1))

    else:

        score = 50

    print("📊 Parsed score:", score)

    return score, response