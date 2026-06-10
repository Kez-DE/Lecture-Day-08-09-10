#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from embedding_provider import get_embedding_function

load_dotenv()
ROOT = Path(__file__).resolve().parent


def retrieve(question: str, top_k: int) -> list[dict]:
    try:
        import chromadb
    except ImportError:
        print("Install: pip install chromadb", file=sys.stderr)
        raise SystemExit(1)

    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb_qwen3")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_collection(name=collection_name, embedding_function=get_embedding_function())
    res = col.query(query_texts=[question], n_results=top_k)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    return [{"text": doc, "metadata": meta or {}} for doc, meta in zip(docs, metas)]


def call_openrouter(question: str, contexts: list[dict]) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing in .env")
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/owl-alpha")
    context_text = "\n\n".join(
        f"[{i}] doc_id={c['metadata'].get('doc_id', '')}\n{c['text']}"
        for i, c in enumerate(contexts, start=1)
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Bạn là CS/IT Helpdesk RAG agent. Trả lời ngắn gọn bằng tiếng Việt, "
                    "chỉ dùng context được cung cấp. Nếu context thiếu, nói không đủ dữ liệu."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nCâu hỏi: {question}",
            },
        ],
        "temperature": 0,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost/day10-lab",
            "X-Title": "Day 10 Lab RAG Agent",
        },
        method="POST",
    )
    context = None
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=120, context=context) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter request failed: HTTP {e.code} {detail}") from e
    return data["choices"][0]["message"]["content"].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG agent using Ollama embeddings + OpenRouter LLM")
    parser.add_argument("question", nargs="?", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--show-context", action="store_true")
    args = parser.parse_args()
    question = args.question or input("Question: ").strip()
    contexts = retrieve(question, args.top_k)
    answer = call_openrouter(question, contexts)
    print(answer)
    if args.show_context:
        print("\n--- context ---")
        for i, c in enumerate(contexts, start=1):
            print(f"{i}. {c['metadata'].get('doc_id', '')}: {c['text'][:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
