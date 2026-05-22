from app.core.ollama_client import generate

def multi_query_expansion(query):

    print("🔹 Multi-query expansion...")

    prompt = f"""
Generate ONLY 2 alternate versions of this query.

Query:
{query}

Return only bullet points.
"""

    response = generate(prompt)

    queries = []

    for line in response.split("\n"):

        line = line.strip()

        if line.startswith("-") or line.startswith("1"):

            queries.append(line)

    # ✅ ONLY 2 QUERIES
    queries = queries[:2]

    print("✅ Generated", len(queries), "queries")

    return queries


