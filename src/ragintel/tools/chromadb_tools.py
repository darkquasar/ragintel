import os
import time
import uuid
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction
from chromadb.utils import embedding_functions
from langchain.docstore.document import Document
from langchain_core.embeddings import Embeddings
from loguru import logger

from ragintel.templates.enums import EmbedderType
from ragintel.utils.ollama_embedding_chroma import OllamaEmbeddingFunction
from ragintel.utils.text_splitter import TextSplitter


class ChromaEmbeddingsAdapter(Embeddings):
    def __init__(self, ef: EmbeddingFunction):
        self.ef = ef

    def embed_documents(self, texts):
        return self.ef(texts)

    def embed_query(self, query):
        return self.ef([query])[0]

class ChromaOps:
    def __init__(self, collection_name: str, embedder: EmbedderType = EmbedderType.CHROMA, db_path: Path = Path("./data/chromadb")):
        logger.info("Initializing ChromaDB")
        # setup Chroma in-memory, for easy prototyping. Can add persistence easily!
        self.client = chromadb.PersistentClient(path=str(db_path))

        self.embedder = embedder

        # Create or Get collection. get_collection, get_or_create_collection, delete_collection also available!
        if embedder == EmbedderType.CHROMA:
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Using Chroma as the embedding function")
        elif embedder == EmbedderType.OPENAI:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(model=os.getenv("OPENAI_EMBEDDINGS_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), )
            logger.info("Using OpenAI as the embedding function")
        elif embedder == EmbedderType.GEMINI:
            self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=os.getenv("GOOGLE_API_KEY"), model_name=os.getenv("GOOGLE_EMBEDDINGS_MODEL"))
            logger.info("Using Google Generative AI as the embedding function")
        elif embedder == EmbedderType.OLLAMA:
            self.ef = OllamaEmbeddingFunction(model_name=os.getenv("OLLAMA_EMBEDDINGS_MODEL"), url=os.getenv("OLLAMA_SERVER_EMBEDDINGS_API_URL"))
            logger.info("Using Ollama as the embedding function")

        self.collection = self.client.get_or_create_collection(collection_name,
                                                               embedding_function=self.ef)


    def embed_documents(self, docs: list[Document], extra_metadata_fields: list[dict] = []):
        # Split the text into sentences
        logger.info("Splitting text into chunks prior to embedding...")
        text_splitter = TextSplitter()
        tokenized_docs = text_splitter.split_text_recursive_char(docs)

        # Add docs to the collection. Can also update and delete.
        logger.info(f"Embedding {len(docs)} documents in ChromaDB...")
        # We need to consider quotas and rate limiting for the embedding services
        if self.embedder == EmbedderType.GEMINI:

            # Split the documents into sublists based on the quota
            logger.debug("Splitting documents into sublists based on the quota...")
            sublists = self.split_docs_by_quota(docs=tokenized_docs, quota_per_minute=100)

            for doc_sublist in sublists:

                self.collection.add(
                    documents=[doc.page_content for doc in doc_sublist], # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                    metadatas=[doc.metadata for doc in doc_sublist], # filter on these!
                    ids=[str(uuid.uuid4()) for doc in doc_sublist], # unique for each doc
                )

                logger.info(f"Added {len(doc_sublist)} documents to the collection")
                logger.debug("Sleeping for 60 seconds to avoid rate limiting...")
                time.sleep(60)  # Sleep for a minute to avoid rate limiting

        if self.embedder == EmbedderType.OLLAMA:

            # Split the documents into sublists based on the quota
            logger.debug("Splitting documents into sublists based on the quota...")
            sublists = self.split_docs_by_quota(docs=tokenized_docs, quota_per_minute=100)

            for doc_sublist in sublists:

                self.collection.add(
                    documents=[doc.page_content for doc in doc_sublist], # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                    metadatas=[doc.metadata for doc in doc_sublist], # filter on these!
                    ids=[str(uuid.uuid4()) for doc in doc_sublist], # unique for each doc
                )

                logger.info(f"Added {len(doc_sublist)} documents to the collection")

    def query_collection(self, query: list[str] | str, n_results: int = 5, top_k: int = 5):
        # Query the collection. Can also filter on metadata!
        if isinstance(query, str):  # Check if it's a single string
            query = [query]  # Convert to a list for consistent handling

        return self.collection.query(
            query_texts=query,
            n_results=n_results)

    def split_docs_by_quota(self, docs: list[Document], quota_per_minute: int = 100) -> list[list[Document]]:
        """
        Splits a list of document contents into sublists based on a quota.

        Args:
            docs: A list of document contents (strings).
            quota_per_minute: The maximum quota allowed per sublist.

        Returns:
            A list of sublists, each containing document contents within the quota.
        """

        sublists = []
        current_sublist = []
        current_count = 0

        for doc in docs:
            if current_count < quota_per_minute:
                current_sublist.append(doc)
                current_count += 1
            else:
                sublists.append(current_sublist)
                current_sublist = [doc]
                current_count = 1

        # Append the last sublist if it's not empty
        if current_sublist:
            sublists.append(current_sublist)
            logger.debug(f"Split documents list into {len(sublists)} sublists")

        return sublists
