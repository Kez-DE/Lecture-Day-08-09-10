from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import List, Sequence


class OllamaEmbeddingFunction:
    def __init__(self, *, model_name: str, base_url: str, timeout: int = 120) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def __call__(self, input: Sequence[str]) -> List[List[float]]:
        texts = list(input)
        payload = {"model": self.model_name, "input": texts}
        try:
            data = self._post_json("/api/embed", payload)
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list):
                return embeddings
        except urllib.error.HTTPError:
            pass

        # Older Ollama servers expose only /api/embeddings and accept one prompt.
        return [
            self._post_json("/api/embeddings", {"model": self.model_name, "prompt": text})[
                "embedding"
            ]
            for text in texts
        ]

    def embed_query(self, input: Sequence[str]) -> List[List[float]]:
        return self(input)

    def embed_documents(self, input: Sequence[str]) -> List[List[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "ollama"

    def get_config(self) -> dict:
        return {
            "url": self.base_url,
            "model_name": self.model_name,
            "timeout": self.timeout,
        }

    @staticmethod
    def validate_config(config: dict) -> None:
        for key in ("url", "model_name", "timeout"):
            if key not in config:
                raise ValueError(f"Missing Ollama embedding config key: {key}")

    @staticmethod
    def build_from_config(config: dict) -> "OllamaEmbeddingFunction":
        return OllamaEmbeddingFunction(
            model_name=config["model_name"],
            base_url=config["url"],
            timeout=int(config["timeout"]),
        )

    def _post_json(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. Start Ollama and pull "
                f"{self.model_name!r} first."
            ) from e


def get_embedding_function():
    provider = os.environ.get("EMBEDDING_PROVIDER", "ollama").strip().lower()
    model_name = os.environ.get("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
    if provider == "ollama":
        return OllamaEmbeddingFunction(
            model_name=model_name,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            timeout=int(os.environ.get("OLLAMA_EMBED_TIMEOUT", "120")),
        )

    if provider == "sentence_transformers":
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER={provider!r}")
