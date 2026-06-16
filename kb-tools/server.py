#!/usr/bin/env python3
"""
HTTP Server for Catholic Knowledge Base.
Flask app with streaming responses and a web chat UI.
"""

import sys, os, json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

sys.path.insert(0, str(Path(__file__).parent))
import engine

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify(engine.check_health())


@app.route("/api/search", methods=["POST"])
def search():
    data = request.json
    query = data.get("query", "")
    mode = data.get("mode", "auto")
    max_results = data.get("max_results", 10)

    if not query:
        return jsonify({"error": "No query provided"}), 400

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

    return jsonify({"results": results, "count": len(results)})


@app.route("/api/query", methods=["POST"])
def query():
    data = request.json
    question = data.get("question", "")
    mode = data.get("mode", "auto")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    result = engine.query(question, mode=mode)
    return jsonify(result)


@app.route("/api/query-stream", methods=["POST"])
def query_stream():
    data = request.json
    question = data.get("question", "")
    mode = data.get("mode", "auto")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    def generate():
        # First, search and assemble context
        if mode == "keyword":
            results = engine.search_keyword(question)
        elif mode == "scripture":
            results = engine.search_scripture(question)
        elif mode == "ccc":
            results = engine.search_ccc(question)
        elif mode == "canon":
            results = engine.search_canon(question)
        elif mode == "semantic":
            results = engine.search_semantic(question)
        else:
            results = engine.search_auto(question)

        # Send sources first
        sources = []
        for r in results[:10]:
            src = {
                "doc_id": r.get("doc_id", ""),
                "path": r.get("path", ""),
                "section": r.get("section_label", r.get("reference", "")),
            }
            if r.get("similarity"):
                src["similarity"] = r["similarity"]
            sources.append(src)

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # Assemble context and stream response
        context = engine.assemble_context(question, results)

        for token in engine.generate_response_stream(question, context):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/documents")
def documents():
    category = request.args.get("category")
    catalog = engine.load_catalog()
    docs = catalog.get("documents", [])
    if category:
        docs = [d for d in docs if d.get("category") == category]
    return jsonify({"documents": docs, "count": len(docs)})


@app.route("/api/document/<path:doc_id>")
def document(doc_id):
    catalog = engine.load_catalog()
    xrefs = engine.load_cross_refs()

    doc_meta = None
    for d in catalog.get("documents", []):
        if d["id"] == doc_id:
            doc_meta = d
            break

    if not doc_meta:
        return jsonify({"error": "Document not found"}), 404

    xref_data = xrefs.get(doc_id, {})
    return jsonify({"document": doc_meta, "cross_references": xref_data})


@app.route("/api/topics")
def topics():
    return jsonify(engine.load_topic_index())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Catholic Knowledge Base Web Server")
    parser.add_argument("--port", "-p", type=int, default=8080)
    parser.add_argument("--host", "-H", default="127.0.0.1")
    parser.add_argument("--debug", "-d", action="store_true")
    args = parser.parse_args()

    print(f"\n  Catholic Knowledge Base — Web UI")
    print(f"  http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
