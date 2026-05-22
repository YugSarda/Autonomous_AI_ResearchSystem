from app.agents.planner import plan
from app.agents.retriever_agent import retrieve
from app.agents.synthesizer import synthesize
from app.agents.critic import critique
from app.agents.self_reflection import reflect

from app.services.metrics import Metrics
from app.services.citation_verifier import verify_citations
from app.core.memory import get_memory, add_memory


def run_agents(query, retriever):

    print("\n🚀 NEW QUERY RECEIVED:", query)

    logs = []
    max_iter = 1
    threshold = 75
    metrics = Metrics()

    # 🧠 MEMORY
    memory = get_memory()
    if memory:
        print("🧠 Using memory context")
        query = query + "\nPrevious context:\n" + str(memory[-3:])

    for i in range(max_iter):

        print(f"\n🔁 ITERATION {i+1}")

        logs.append(f"Iteration {i+1}")

        # 🔹 PLAN
        print("🧠 Planning...")
        sub_questions = plan(query)
        print("✅ Sub-questions:", sub_questions)

        logs.append(f"Planned: {sub_questions}")

        # 🔹 RETRIEVAL
        print("🔍 Retrieving for each sub-question...")
        results = []
        for q in sub_questions:
            print(f"   → Retrieving: {q}")
            res = retrieve(q, retriever)
            results.append(res)

        print("✅ Retrieval done")

        metrics.log_retrieval(len(results))

        # 🔹 SYNTHESIS
        print("🧩 Synthesizing final answer...")
        answer = synthesize(results, query)
        print("✅ Synthesis done")

        # 🔹 CRITIC
        print("🧪 Evaluating answer...")
        score, feedback = critique(answer)
        print(f"📊 Score: {score}")
        print(f"📝 Feedback: {feedback}")

        logs.append(f"Score: {score}")
        logs.append(f"Feedback: {feedback}")

        # 🔹 COLLECT DOCS
        print("📚 Collecting documents for citation...")
        all_docs = []
        for r in results:
            all_docs.extend(r["docs"])

        # 🔹 VERIFY CITATIONS
        print("🔒 Verifying citations...")
        answer = verify_citations(answer, all_docs)
        print("✅ Citation verification done")

        # 🔹 CHECK QUALITY
        if score >= threshold:
            print("✅ Answer accepted")
            add_memory(query, answer)

            return {
                "answer": answer,
                "confidence": score,
                "sources": [doc.metadata for doc in all_docs],
                "metrics": metrics.finish(),
                "logs": logs
            }

        # 🔁 RETRY
        print("⚠️ Score too low → improving query...")
        query = reflect(answer)

    print("⚠️ Max iterations reached")

    add_memory(query, answer)

    return {
        "answer": answer,
        "confidence": score,
        "sources": [],
        "metrics": metrics.finish(),
        "logs": logs
    }