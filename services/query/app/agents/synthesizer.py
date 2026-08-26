import os
# OLD: from app.core.ollama_client import generate
from app.core.llm_client import generate
from typing import List, Dict, Any, Optional


def synthesize(results, query, memory_context: str = None, test_mode: bool = True):
    """
    Synthesize retrieved results into a coherent answer with inline citations.
    
    Returns a dict with:
        - answer (str): The generated answer with inline citations like [1], [2]
        - citations (List[Dict]): Mapping of citation numbers to source info
    """
    print("🧩 Synthesizer Agent Running...")

    combined = []
    citation_map = {}  # index -> {file_name, text_snippet}
    citation_counter = 0

    for r in results:
        docs = r.get("docs", [])
        for doc in docs:
            text = doc.text if hasattr(doc, "text") else str(doc)
            
            # Build citation entry
            citation_counter += 1
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            source_path = metadata.get("source", "Unknown")
            file_name = os.path.basename(source_path) if source_path != "Unknown" else "Unknown"
            
            citation_map[citation_counter] = {
                "number": citation_counter,
                "file_name": file_name,
                "file_path": source_path,
                "text_snippet": text[:300].strip(),
                "score": round(doc.score, 4) if hasattr(doc, "score") and doc.score else None,
            }
            
            # Add source label to the context so the LLM can reference it
            combined.append(f"[Source {citation_counter}]: {text}")

    context = "\n\n".join(combined)

    # Cap context so local-LLM prompt evaluation stays reasonable.
    # (Full doc context still gets quoted for citations; only prompt size is bounded.)
    MAX_CONTEXT_CHARS = 4000
    if len(context) > MAX_CONTEXT_CHARS:
        print(f"✂️ Truncating context from {len(context)} to {MAX_CONTEXT_CHARS} chars")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[...context truncated for prompt size...]"

    # Fallback protection
    if not context.strip():
        return {
            "answer": "No relevant information found in uploaded documents.",
            "citations": [],
        }

    # Build memory section if available
    memory_section = ""
    if memory_context:
        memory_section = f"""
=== PREVIOUS CONVERSATION MEMORY ===
{memory_context}

Use the above memory for context about previous conversations.
If the current question is a follow-up, use memory to maintain continuity.
=====================================
"""

    prompt = f"""
You are a grounded research assistant.
{memory_section}
Answer the question using ONLY the provided context.

CRITICAL INSTRUCTIONS FOR CITATIONS:
- Each source is labeled as [Source 1], [Source 2], etc.
- When you use information from a source, cite it inline like [1], [2]
- If you combine information from multiple sources, cite all of them like [1][2]
- Every factual claim MUST be supported by at least one citation
- If information is missing, say: 'The uploaded documents do not contain enough information.'

CONTEXT:
{context}

QUESTION:
{query}

Remember: Answer ONLY from context. Use inline citations [N] for every claim.
"""
    answer = generate(prompt)

    print("✅ Synthesis completed with citations")
    print(f"📚 Citations generated: {len(citation_map)}")

    return {
        "answer": answer,
        "citations": list(citation_map.values()),
    }
