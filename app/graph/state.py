"""Research System - Typed state model for LangGraph orchestration."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResearchState(BaseModel):
    """State for the research agent orchestration graph.

    Tracks the full lifecycle of a research query through planning,
    retrieval, synthesis, critique, and optional retry loops.
    """
    # --- Query & Session ---
    query: str = Field(..., min_length=1, max_length=10000, description="Original user query")
    session_id: str = Field(default="default_session", description="Session identifier")
    trace_id: str = Field(default="", description="Distributed tracing ID")

    # --- Planning ---
    sub_questions: List[str] = Field(default_factory=list, description="Sub-questions from planner")

    # --- Retrieval ---
    retrieval_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results per sub-question")
    retrieval_confidence: List[float] = Field(default_factory=list, description="Confidence score per sub-question (0-1)")
    context: Optional[str] = Field(default=None, description="Combined context from retrieval")

    # --- Synthesis ---
    answer: Optional[str] = Field(default=None, description="Generated answer from synthesizer")
    all_docs: List[Any] = Field(default_factory=list, description="All retrieved documents for citation")

    # --- Citations ---
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Rich citation info: file name, snippet, score")

    # --- Critique ---
    score: int = Field(default=0, ge=0, le=100, description="Quality score from critic")
    feedback: Optional[str] = Field(default=None, description="Critic feedback")

    # --- Control Flow ---
    iteration_count: int = Field(default=0, ge=0, le=5, description="Current retry iteration")
    max_iterations: int = Field(default=1, description="Maximum retry attempts")
    quality_threshold: int = Field(default=75, description="Minimum acceptable score")
    test_mode: bool = Field(default=True, description="If True, skip critique/reflect/cite for fast testing")

    # --- Memory ---
    memory_context: Optional[str] = Field(default=None, description="Context from short/long-term memory")
    memory_hit: bool = Field(default=False, description="Whether query was answered from memory cache")
    cached_answer: Optional[str] = Field(default=None, description="Answer retrieved from memory cache")
    matched_query: Optional[str] = Field(default=None, description="The query that was matched in memory")
    similarity_score: Optional[float] = Field(default=None, description="Cosine similarity score for memory match")

    # --- Error Handling ---
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_node: Optional[str] = Field(default=None, description="Node where error occurred")

    # --- Observability ---
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Latency, token counts etc.")

    class Config:
        """Pydantic config."""
        extra = "allow"
