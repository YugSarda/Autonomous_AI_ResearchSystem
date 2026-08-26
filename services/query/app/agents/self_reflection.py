# OLD: from app.core.ollama_client import generate
from app.core.llm_client import generate
from typing import List, Any


def reflect(
    answer: str,
    question: str = "",
    docs: List[Any] = None,
    feedback: str = "",
    score: int = 0,
    confidence_scores: List[float] = None,
):
    """
    Analyze what went wrong and generate an improved query for retry.

    Receives the full context: original question, retrieved documents,
    critique feedback, quality score, and retrieval confidence scores.

    Returns an improved query string that addresses the identified gaps.
    """
    # Build doc summary
    doc_summary = ""
    if docs:
        doc_snippets = []
        for i, doc in enumerate(docs[:5]):
            text = doc.text if hasattr(doc, "text") else str(doc)
            snippet = text[:300].strip()
            if len(text) > 300:
                snippet += "..."
            doc_snippets.append(f"[Doc {i+1}]: {snippet}")
        doc_summary = "\n\n".join(doc_snippets)
    else:
        doc_summary = "No documents provided."

    confidence_str = ""
    if confidence_scores:
        confidence_str = ", ".join([f"{c:.2f}" for c in confidence_scores])

    prompt = f"""
You are a self-reflection agent for a research system. Your job is to analyze what went wrong and generate an IMPROVED query to fix the issues.

CONTEXT:
===========
ORIGINAL QUESTION: {question}

===========
GENERATED ANSWER: {answer}

===========
RETRIEVED DOCUMENTS:
{doc_summary}

===========
QUALITY SCORE: {score}/100

===========
RETRIEVAL CONFIDENCE SCORES: [{confidence_str}]

===========
CRITIQUE FEEDBACK:
{feedback}

===========
ANALYSIS INSTRUCTIONS:
1. Identify what information is MISSING from the answer based on the critique feedback.
2. Check if the retrieved documents contain relevant info that the answer failed to include.
3. Determine if the original query was too narrow or poorly focused.
4. If retrieval confidence is low, consider how to make the query more searchable.

OUTPUT:
Generate a SINGLE improved query that will retrieve better documents and produce a more complete answer.
The improved query should be:
- More specific than the original
- Targeted at the missing details identified in the feedback
- Formulated to retrieve documents that fill the gaps

Improved Query:
"""
    improved_query = generate(prompt)
    print("🔄 Self-reflection generated improved query")
    print(f"   Original: {question[:80]}...")
    print(f"   Improved: {improved_query[:80]}...")
    return improved_query