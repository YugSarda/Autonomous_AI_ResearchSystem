from app.core.ollama_client import generate
import json
import re
from typing import List
from pydantic import BaseModel, Field


class PlanningOutput(BaseModel):
    """Structured output from the planner agent."""
    sub_questions: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Focused retrieval sub-questions derived from the user query"
    )


def _extract_json(raw: str) -> str:
    """Extract a JSON object from the LLM response, handling markdown fences."""
    # Try to find JSON inside ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    match = re.search(pattern, raw)
    if match:
        return match.group(1).strip()

    # Find the first { and last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1].strip()

    return raw.strip()


def plan(query: str) -> List[str]:
    """
    Generate sub-questions from the user query using the planner agent.
    
    Returns a validated list of sub-questions via JSON structured output.
    Falls back to the original query on parse failure.
    """
    print("🧠 Planner Agent Running...")

    prompt = f"""
You are a research planning agent.

Break the user query into EXACTLY 2 focused retrieval sub-questions.

Rules:
- Each sub-question should target a distinct aspect of the query.
- Sub-questions must be self-contained and retrievable from documents.
- Return ONLY valid JSON, no markdown fences, no extra text.

Output format:
{{"sub_questions": ["question 1", "question 2"]}}

User Query:
{query}
"""

    response = generate(prompt)

    print("📄 Raw planner response:")
    print(response)

    try:
        json_str = _extract_json(response)
        parsed = json.loads(json_str)

        # Validate with Pydantic
        validated = PlanningOutput(**parsed)
        questions = validated.sub_questions[:2]  # Cap at 2 as per original behavior

        print("✅ Planner generated", len(questions), "sub-questions")
        return questions

    except (json.JSONDecodeError, Exception) as e:
        print(f"⚠️ Planner JSON parse failed ({e}), falling back to line-based parsing")

        # Fallback: original line-based parsing
        questions = []
        for line in response.split("\n"):
            line = line.strip()
            if len(line) > 5:
                line = re.sub(r"^[-•\d\.\)\s]+", "", line)
                questions.append(line)

        if not questions:
            questions = [query]

        questions = questions[:2]
        print("✅ Planner generated", len(questions), "sub-questions (fallback)")
        return questions