"""
This is an adaptation of the OllamaEmbeddingFunction class from the ChromaDB API to work with a version of ChromaDB that is not compatible yet with the rest of the Ragintel Packages, specifically Crewai
"""

from typing import cast

import httpx
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from loguru import logger


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    This class is used to generate embeddings for a list of texts using the Ollama Embedding API (https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings).
    """

    def __init__(self, url: str, model_name: str) -> None:
        """
        Initialize the Ollama Embedding Function.

        Args:
            url (str): The URL of the Ollama Server.
            model_name (str): The name of the model to use for text embeddings. E.g. "nomic-embed-text" (see https://ollama.com/library for available models).
        """
        self._api_url = f"{url}"
        self._model_name = model_name
        self._session = httpx.Client()

    def __call__(self, input: Documents | str) -> Embeddings:
        """
        Get the embeddings for a list of texts.

        Args:
            input (Documents): A list of texts to get embeddings for.

        Returns:
            Embeddings: The embeddings for the texts.

        Example:
            >>> ollama_ef = OllamaEmbeddingFunction(
            ...     url="http://localhost:11434/api/embed", model_name="nomic-embed-text"
            ... )
            >>> texts = ["Hello, world!", "How are you?"]
            >>> embeddings = ollama_ef(texts)
        """
        # Call Ollama Server API for each document
        texts = input if isinstance(input, list) else [input]
        embeddings = [
            self._session.post(
                self._api_url, json={"model": self._model_name, "input": text}
            ).json()
            for text in texts
        ]

        return cast(
            Embeddings,
            [item["embeddings"][0] for item in embeddings if "embeddings" in item],
        )
