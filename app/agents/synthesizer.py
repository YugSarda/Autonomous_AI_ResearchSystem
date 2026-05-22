from app.core.ollama_client import generate


def synthesize(results,query):

    print("🧩 Synthesizer Agent Running...")

    combined = []

    for r in results:

        docs = r.get("docs", [])

        for doc in docs:

            if hasattr(doc, "text"):

                combined.append(doc.text)

            else:

                combined.append(str(doc))

    context = "\n\n".join(combined)

    # Fallback protection
    if not context.strip():

        return "No relevant information found in uploaded documents."

    prompt = f"""
You are a grounded research assistant.

Answer the question ONLY using the provided context.

If information is missing,
say:
'The uploaded documents do not contain enough information.'

CONTEXT:
{context}

QUESTION:
{query}
"""
    answer = generate(prompt)

    print("✅ Synthesis completed")

    return answer