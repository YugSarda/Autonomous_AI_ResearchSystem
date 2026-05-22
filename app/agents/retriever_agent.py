from app.services.query_pipeline import run_query_pipeline

def retrieve(sub_query, retriever):
    answer, docs = run_query_pipeline(sub_query, retriever)
    return {
        "query": sub_query,
        "answer": answer,
        "docs": docs
    }