from app.core.ollama_client import generate
import re
from typing import List, Any


def critique(answer: str, question: str = "", docs: List[Any] = None):
    """
    Evaluate the answer for quality, faithfulness to retrieved documents,
    completeness against the question, and hallucination risk.

    Args:
        answer: The generated answer to evaluate.
        question: The original user query (for completeness check).
        docs: Retrieved documents (for faithfulness/groundedness check).

    Returns:
        Tuple of (score: int, feedback: str)
    """
    print("🧪 Critic Agent Running...")

    # Build a summary of retrieved docs for the prompt
    doc_summary = ""
    if docs:
        doc_snippets = []
        for i, doc in enumerate(docs[:5]):  # Limit to first 5 docs to keep prompt manageable
            text = doc.text if hasattr(doc, "text") else str(doc)
            snippet = text[:300].strip()
            if len(text) > 300:
                snippet += "..."
            score = round(doc.score, 3) if hasattr(doc, "score") and doc.score else "N/A"
            doc_snippets.append(f"[Doc {i+1}] (score={score}): {snippet}")
        doc_summary = "\n\n".join(doc_snippets)
    else:
        doc_summary = "No documents provided."

    prompt = f"""
You are a strict research answer evaluator. Evaluate the answer based on:

1. **Faithfulness** (0-40 pts): Is every claim in the answer supported by the retrieved documents? Mark down for hallucination or unsupported claims.
2. **Completeness** (0-30 pts): Does the answer fully address the original question? Are there missing details that the documents contain?
3. **Relevance** (0-20 pts): Is the answer focused on the question without digression?
4. **Clarity** (0-10 pts): Is the answer well-structured and clear?

Return STRICTLY in this format:

Score: <total 0-100>
Missing Parts: <what's missing from the answer>
Hallucination Risk: <any claims not supported by docs>
Faithfulness Issues: <specific unsupported claims>
Improvement Suggestions: <how to fix>

===========
QUESTION:
{question}

===========
ANSWER:
{answer}

===========
RETRIEVED DOCUMENTS:
{doc_summary}
===========

Be critical and thorough. Score 0 if the answer is completely off-topic or hallucinated.
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
        # Clamp score to 0-100
        score = max(0, min(100, score))
    else:
        score = 50

    print("📊 Parsed score:", score)

    return score, response