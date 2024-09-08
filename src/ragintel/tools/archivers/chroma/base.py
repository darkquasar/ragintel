import os
import time
import uuid
from pathlib import Path
from typing import Literal

import chromadb
from chromadb.utils import embedding_functions
from langchain.docstore.document import Document
from llama_index.core import Document as LlamaDocument
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from ragintel.utils.adaptors.chroma.ollama_embedding_chroma import OllamaEmbeddingFunction
from ragintel.utils.enums import EmbedderType
from ragintel.utils.text_splitter import TextSplitter


class ChromaOps:
    def __init__(
        self,
        collection_name: str,
        embedder: EmbedderType = EmbedderType.CHROMA,
        db_path: Path | None = None,
    ):
        logger.info("Initializing ChromaDB")

        if db_path is None:
            db_path = Path(os.getenv("CHROMA_DB_PERSIST_DIRECTORY", "./data/chromadb"))

        # setup ChromaDB client
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.embedder = embedder

        # Create or Get collection. get_collection, get_or_create_collection, delete_collection also available!
        if embedder == EmbedderType.CHROMA:
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Using Chroma as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name, embedding_function=self.ef
            )

        elif embedder == EmbedderType.OPENAI:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(
                model=os.getenv("OPENAI_EMBEDDINGS_MODEL"),
                api_key=os.getenv("OPENAI_API_KEY"),
            )
            logger.info("Using OpenAI as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name, embedding_function=self.ef
            )

        elif embedder == EmbedderType.GEMINI:
            self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=os.getenv("GOOGLE_API_KEY"), model_name=os.getenv("GOOGLE_EMBEDDINGS_MODEL")
            )
            logger.info("Using Google Generative AI as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name, embedding_function=self.ef
            )

        elif embedder == EmbedderType.OLLAMA:
            self.ef = OllamaEmbeddingFunction(
                model_name=os.getenv("OLLAMA_EMBEDDINGS_MODEL"),
                url=os.getenv("OLLAMA_SERVER_EMBEDDINGS_API_URL"),
            )
            logger.info("Using Ollama as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name, embedding_function=self.ef
            )

            # Now setup all the ChromaDB storage layers
            # Set up ChromaVectorStore and VectorStoreIndex (which is the LlamaIndex storage layer over the ChromaDB collection)
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            # Define embedding function
            ollama_model_name = os.getenv("OLLAMA_EMBEDDINGS_MODEL")
            ollama_url = os.getenv("OLLAMA_SERVER_URL")
            self.embed_model = OllamaEmbedding(model_name=ollama_model_name, base_url=ollama_url)

    def embed_documents(
        self, documents: list[Document | LlamaDocument], extra_metadata_fields: dict | None = None
    ):
        """ """
        if not documents:  # Check if the list is empty
            msg = "No documents provided to embed"
            raise ValueError(msg)

        first_doc = documents[0]

        if isinstance(first_doc, Document):
            return self.embed_documents_from_langchain_docs(
                docs=documents, extra_metadata_fields=extra_metadata_fields
            )

        if isinstance(first_doc, LlamaDocument):
            return self.embed_documents_from_llamaindex_docs(
                docs=documents, extra_metadata_fields=extra_metadata_fields
            )
        return None

    def embed_documents_from_langchain_docs(
        self, docs: list[Document], extra_metadata_fields: dict | None = None
    ):
        # Update metadata with extra fields if provided
        if extra_metadata_fields is not None:
            for doc in docs:
                doc.metadata.update(extra_metadata_fields)

        # Split the text into sentences
        logger.info("Splitting text into chunks prior to embedding...")
        text_splitter = TextSplitter()
        tokenized_docs = text_splitter.split_text_recursive_char(docs)

        # Add docs to the collection. Can also update and delete.
        logger.info(f"Embedding {len(docs)} documents in ChromaDB...")
        # We need to consider quotas and rate limiting for the embedding services
        if self.embedder == EmbedderType.GEMINI:
            # Split the documents into sublists based on the quota
            logger.debug(
                "Splitting documents into buckets of documents based on the quota for Gemini..."
            )
            sublists = self.split_docs_by_quota(docs=tokenized_docs, quota_per_minute=100)

            for doc_sublist in sublists:
                self.collection.add(
                    documents=[
                        doc.page_content for doc in doc_sublist
                    ],  # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                    metadatas=[doc.metadata for doc in doc_sublist],  # filter on these!
                    ids=[str(uuid.uuid4()) for doc in doc_sublist],  # unique for each doc
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
                    documents=[
                        doc.page_content for doc in doc_sublist
                    ],  # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                    metadatas=[doc.metadata for doc in doc_sublist],  # filter on these!
                    ids=[str(uuid.uuid4()) for doc in doc_sublist],  # unique for each doc
                )

                logger.info(f"Added {len(doc_sublist)} documents to the collection")

    def embed_documents_from_llamaindex_docs(
        self, docs: list[LlamaDocument], extra_metadata_fields: dict | None = None
    ):
        # Update metadata with extra fields if provided
        if extra_metadata_fields is not None:
            for doc in docs:
                doc.metadata.update(extra_metadata_fields)

        # Add docs to the collection. Can also update and delete.
        logger.info(f"[LlamaIndex] Embedding {len(docs)} documents in ChromaDB...")

        # We need to consider quotas and rate limiting for the embedding services
        if self.embedder == EmbedderType.GEMINI:
            # Split the documents into sublists based on the quota
            logger.debug("[LlamaIndex] TO BE IMPLEMENTED")

            """TBD: Implement the splitting of documents into sublists for LlamaIndex as well."""

            """
            for doc_sublist in sublists:
                self.collection.add(
                    documents=[
                        doc.page_content for doc in doc_sublist
                    ],  # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                    metadatas=[doc.metadata for doc in doc_sublist],  # filter on these!
                    ids=[str(uuid.uuid4()) for doc in doc_sublist],  # unique for each doc
                )

                logger.info(f"Added {len(doc_sublist)} documents to the collection")
                logger.debug("Sleeping for 60 seconds to avoid rate limiting...")
                time.sleep(60)  # Sleep for a minute to avoid rate limiting
            """
            return

        if self.embedder == EmbedderType.OLLAMA:
            logger.debug("[LlamaIndex] using Ollama as the embedding function")

            self.index = VectorStoreIndex.from_documents(
                docs, storage_context=self.storage_context, embed_model=self.embed_model
            )

            logger.info(f"[LlamaIndex] Added {len(docs)} documents to the collection")

    def query_collection(
        self,
        query: list[str] | str,
        engine: Literal["LlamaIndex", "ChromaDB"] | None = None,
        top_k: int = 5,
    ) -> list | str:
        """
        Queries the collection using the specified query and engine.
        Args:
            query (list[str] | str): The query or list of queries to search for.
            engine (Optional[Literal["LlamaIndex", "ChromaDB"]]): The engine to use for querying. Defaults to None.
            n_results (int): The maximum number of results to return. Defaults to 5.
            top_k (int): The maximum number of top-k results to consider. Defaults to 5.
        Returns:
            Union[list, str]: The retrieved nodes from the collection.
        Raises:
            None
        """

        if engine is None:
            engine = "ChromaDB"  # Set default if None

        if engine == "LlamaIndex".lower():
            if not hasattr(self, "index"):
                logger.warning(
                    "No LlamaIndex retriever instance found. Initiating ChromaDB Retriever."
                )
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store, embed_model=self.embed_model
                )

            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)

        elif engine == "ChromaDB".lower():
            if isinstance(query, str):  # Check if it's a single string
                query = [query]  # Convert to a list for consistent handling
            nodes = self.collection.query(query_texts=query, n_results=top_k)

        return nodes

    def split_docs_by_quota(
        self, docs: list[Document], quota_per_minute: int = 100
    ) -> list[list[Document]]:
        """
        Splits a list of document contents into sublists based on an allowed quota per minute. Useful for embedding APIs that are rate limited like Google's one.

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
