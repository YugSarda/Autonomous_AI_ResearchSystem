# from app.core.ollama_client import generate

# def plan(query):
#     prompt = f"""
# Break this into 2 sub-questions:
# {query}
# """
#     res = generate(prompt)
#     return [q.strip() for q in res.split("\n") if q.strip()]

from app.core.ollama_client import generate
import re


def plan(query: str):

    print("🧠 Planner Agent Running...")

    prompt = f"""
You are a research planning agent.

Break the user query into EXACTLY 2 focused retrieval sub-questions.

RULES:
- Return ONLY the questions
- One question per line
- No explanations
- No numbering
- No bullets

User Query:
{query}
"""

    response = generate(prompt)

    print("📄 Raw planner response:")
    print(response)

    questions = []

    for line in response.split("\n"):

        line = line.strip()

        if len(line) > 5:

            # Remove bullets/numbers safely
            line = re.sub(r"^[-•\d\.\)\s]+", "", line)

            questions.append(line)

    # Fallback
    if not questions:

        questions = [query]

    questions = questions[:2]

    print("✅ Planner generated", len(questions), "sub-questions")

    return questions