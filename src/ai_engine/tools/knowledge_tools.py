"""
Knowledge & Search Tools
Provide knowledge base lookup and web search stubs for the AI engine.
Replace implementations with real services when available.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from src.ai_engine.core.tools import registry
from src.logger import get_logger

logger = get_logger(__name__)


class QueryKnowledgeArgs(BaseModel):
    query: str = Field(..., description="Search query for the internal knowledge base")
    top_k: int = Field(3, description="Number of results to return")


class SearchWebArgs(BaseModel):
    query: str = Field(..., description="Web search query")
    top_k: int = Field(3, description="Number of results to return")


@registry.register("query_knowledge_base", "Query the internal knowledge base", QueryKnowledgeArgs)
async def query_knowledge_base(query: str, top_k: int = 3):
    """Stubbed KB lookup. Replace with real vector search when available."""
    logger.info("KB query", extra={"query": query, "top_k": top_k})
    # TODO: Integrate with actual knowledge base / vector store
    mock_results = [
        {"title": "KB Doc 1", "snippet": f"Relevant info about {query}", "score": 0.9},
        {"title": "KB Doc 2", "snippet": f"Additional context on {query}", "score": 0.7},
    ][:top_k]
    return {"results": mock_results, "source": "knowledge_base"}


@registry.register("search_web", "Perform a lightweight web search", SearchWebArgs)
async def search_web(query: str, top_k: int = 3):
    """Stubbed web search. Replace with real API (e.g., SerpAPI/Bing)."""
    logger.info("Web search", extra={"query": query, "top_k": top_k})
    # TODO: Call external search provider
    mock_results = [
        {"title": "Search Result 1", "url": "https://example.com/1", "snippet": f"Snippet about {query}"},
        {"title": "Search Result 2", "url": "https://example.com/2", "snippet": f"More on {query}"},
    ][:top_k]
    return {"results": mock_results, "source": "web"}
