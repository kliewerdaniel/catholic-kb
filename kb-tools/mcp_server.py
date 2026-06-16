#!/usr/bin/env python3
"""
MCP Server for Catholic Knowledge Base.
Exposes the knowledge base as MCP tools for any MCP-compatible client.
"""

import sys, os, json
from pathlib import Path

# Add kb-tools to path for engine imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
import engine

# Create MCP server
mcp = FastMCP(
    "Catholic Knowledge Base",
    instructions="A comprehensive Catholic knowledge base with Scripture, Catechism, Canon Law, Church Fathers, and Magisterial documents. Search, query, and synthesize across 212 documents.",
)


@mcp.tool()
def search_knowledge(
    query: str,
    mode: str = "auto",
    max_results: int = 10,
) -> str:
    """
    Search the Catholic knowledge base.

    Args:
        query: The search query (natural language, Scripture reference, CCC paragraph, or canon number)
        mode: Search mode - "auto" (detect automatically), "semantic" (conceptual), "keyword" (exact match),
              "scripture" (Bible reference like "John 3:16"), "ccc" (Catechism paragraph like "CCC 279"),
              "canon" (Canon Law like "Canon 212")
        max_results: Maximum number of results to return (default 10)

    Returns:
        JSON string with search results including document paths, sections, and relevance scores.
    """
    if mode == "keyword":
        results = engine.search_keyword(query, max_results=max_results)
    elif mode == "scripture":
        results = engine.search_scripture(query, max_results=max_results)
    elif mode == "ccc":
        results = engine.search_ccc(query, max_results=max_results)
    elif mode == "canon":
        results = engine.search_canon(query, max_results=max_results)
    elif mode == "semantic":
        results = engine.search_semantic(query, max_results=max_results)
    else:
        results = engine.search_auto(query, max_results=max_results)

    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def query_knowledge(
    question: str,
    mode: str = "auto",
) -> str:
    """
    Ask a question about Catholic doctrine and get a sourced answer.
    Searches the knowledge base, assembles relevant sources, and generates
    a response using the local LLM.

    Args:
        question: The question to answer (e.g., "What does the Church teach about the Eucharist?")
        mode: Search mode - "auto", "semantic", "keyword", "scripture", "ccc", "canon"

    Returns:
        JSON string with the answer, sources consulted, and search mode used.
    """
    result = engine.query(question, mode=mode)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def lookup_scripture(
    reference: str,
) -> str:
    """
    Look up a specific Scripture reference and find all documents that cite it.

    Args:
        reference: Scripture reference (e.g., "John 3:16", "Genesis 1:1", "Romans 8:28")

    Returns:
        JSON string with the Scripture text location and all documents referencing this passage.
    """
    results = engine.search_scripture(reference)
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def lookup_ccc(
    paragraph: str,
) -> str:
    """
    Look up a specific Catechism of the Catholic Church paragraph.

    Args:
        paragraph: CCC paragraph number (e.g., "279", "1333", "1213-1284")

    Returns:
        JSON string with the CCC text and documents referencing this paragraph.
    """
    results = engine.search_ccc(paragraph)
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def lookup_canon(
    canon: str,
) -> str:
    """
    Look up a specific canon from the Code of Canon Law (1983).

    Args:
        canon: Canon number (e.g., "212", "915", "1398")

    Returns:
        JSON string with the canon text and documents referencing it.
    """
    results = engine.search_canon(canon)
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def get_sources(
    doc_id: str,
) -> str:
    """
    Get detailed information about a specific document in the knowledge base.

    Args:
        doc_id: Document ID (e.g., "scripture/genesis", "magisterium/ccc/part2-ch2",
                "magisterium/encyclicals/veritatis_splendor")

    Returns:
        JSON string with document metadata, cross-references, and content summary.
    """
    catalog = engine.load_catalog()
    xrefs = engine.load_cross_refs()

    # Find document in catalog
    doc_meta = None
    for d in catalog.get("documents", []):
        if d["id"] == doc_id:
            doc_meta = d
            break

    if not doc_meta:
        return json.dumps({"error": f"Document not found: {doc_id}"})

    # Get cross-references
    xref_data = xrefs.get(doc_id, {})

    result = {
        "document": doc_meta,
        "cross_references": xref_data,
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def list_documents(
    category: str = None,
) -> str:
    """
    List all documents in the knowledge base, optionally filtered by category.

    Args:
        category: Optional category filter - "scripture", "magisterium", "canonlaw",
                  "liturgy", "fathers", "doctorate", "social-teaching", "mariology"

    Returns:
        JSON string with document list including IDs, titles, and metadata.
    """
    catalog = engine.load_catalog()
    docs = catalog.get("documents", [])

    if category:
        docs = [d for d in docs if d.get("category") == category]

    return json.dumps(docs, indent=2, ensure_ascii=False)


@mcp.tool()
def system_health() -> str:
    """
    Check the health of the Catholic Knowledge Base system.
    Returns status of Ollama, models, indexes, and document counts.

    Returns:
        JSON string with system health information.
    """
    health = engine.check_health()
    return json.dumps(health, indent=2, ensure_ascii=False)


# Expose catalog as a resource
@mcp.resource("kb://catalog")
def get_catalog_resource() -> str:
    """Get the full document catalog."""
    catalog = engine.load_catalog()
    return json.dumps(catalog, indent=2, ensure_ascii=False)


@mcp.resource("kb://topics")
def get_topics_resource() -> str:
    """Get the topic index."""
    topics = engine.load_topic_index()
    return json.dumps(topics, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
