import os
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import chromadb
from chromadb.utils import embedding_functions
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core import Document as LlamaDocument
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import LangchainNodeParser
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.vector_stores import (
    FilterCondition,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from ragintel.binders.helpers.adaptors.chroma import OllamaEmbeddingFunction
from ragintel.binders.helpers.adaptors.documents import (
    LangChainDocumentSplitter,
)
from ragintel.binders.helpers.enums import EmbedderType


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
                collection_name,
                embedding_function=self.ef,  # type: ignore
            )

        elif embedder == EmbedderType.OPENAI:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(
                model_name=os.getenv("OPENAI_EMBEDDINGS_MODEL"),  # type: ignore
                api_key=os.getenv("OPENAI_API_KEY"),
            )
            logger.info("Using OpenAI as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name,
                embedding_function=self.ef,  # type: ignore
            )

        elif embedder == EmbedderType.GEMINI:
            self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=os.getenv("GOOGLE_API_KEY"),
                model_name=os.getenv("GOOGLE_EMBEDDINGS_MODEL"),  # type: ignore
            )
            logger.info("Using Google Generative AI as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name,
                embedding_function=self.ef,  # type: ignore
            )

        elif embedder == EmbedderType.OLLAMA:
            self.ef = OllamaEmbeddingFunction(
                model_name=os.getenv("OLLAMA_EMBEDDINGS_MODEL"),  # type: ignore
                url=os.getenv("OLLAMA_SERVER_EMBEDDINGS_API_URL"),  # type: ignore
            )
            logger.info("Using Ollama as the embedding function")
            # Initialize ChromaDB client and collection
            self.collection = self.client.get_or_create_collection(
                collection_name,
                embedding_function=self.ef,  # type: ignore
            )

            # Now setup all the ChromaDB storage layers
            # Set up ChromaVectorStore and VectorStoreIndex (which is the LlamaIndex storage layer over the ChromaDB collection)
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store, docstore=SimpleDocumentStore()
            )
            # Define embedding function
            ollama_model_name = os.getenv("OLLAMA_EMBEDDINGS_MODEL")
            ollama_url = os.getenv("OLLAMA_SERVER_URL")
            self.embed_model = OllamaEmbedding(model_name=ollama_model_name, base_url=ollama_url)  # type: ignore

        self.llama_index_ingestion_pipe_persist_dir = os.getenv(
            "LLAMA_INDEX_INGESTION_PIPELINE_PERSIST_DIR", "data/ingestion_pipe"
        )

    def _load_or_create_docstore(
        self, docstore_persist_dir: Path | None = Path("data/docstore")
    ) -> SimpleDocumentStore:
        """Loads a SimpleDocumentStore from disk if it exists, otherwise
           creates a new one. This is an internal method.

        Returns:
            A SimpleDocumentStore instance.
        """
        try:
            docstore = SimpleDocumentStore.from_persist_dir(docstore_persist_dir)

        except FileNotFoundError:
            docstore = SimpleDocumentStore()

        return docstore

    def _load_or_create_ingestion_pipeline(
        self,
        pipeline_persist_dir: Path | None = Path("data/ingestion_pipe"),
        node_splitting_pipeline: bool = True,
        node_splitter: str = "",
    ) -> IngestionPipeline:
        """
        Loads an IngestionPipeline from disk if it exists, otherwise creates a new one. This is an internal method.

        Args:
            pipeline_persist_dir (Union[Path, None]): The directory to persist the pipeline.
            node_splitting_pipeline (bool): Whether to split documents into node chunks prior to embedding.

        Returns:
            IngestionPipeline: An instance of IngestionPipeline.
        """

        if self.llama_index_ingestion_pipe_persist_dir is not None:
            pipeline_persist_dir = Path(self.llama_index_ingestion_pipe_persist_dir)

        try:
            pipeline = IngestionPipeline(
                transformations=[
                    LangchainNodeParser(
                        RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=20)
                    ),
                    self.embed_model,
                ],
                vector_store=self.vector_store,
                docstore=SimpleDocumentStore(),
            )
            pipeline.load(persist_dir=str(pipeline_persist_dir))  # type: ignore
            logger.info(f"Loaded Ingestion Pipeline from {pipeline_persist_dir}")

        except FileNotFoundError:
            logger.info(
                f"Ingestion Pipeline not found at {pipeline_persist_dir}. Creating a new one..."
            )

            if node_splitting_pipeline:
                # Set up the llamaindex ingestion pipeline
                logger.debug("We will split documents into node chunks prior to embedding...")
                pipeline = IngestionPipeline(
                    transformations=[
                        LangchainNodeParser(
                            RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=20)
                        ),
                        self.embed_model,
                    ],
                    vector_store=self.vector_store,
                    docstore=SimpleDocumentStore(),
                )

            else:
                # Set up the llamaindex ingestion pipeline
                logger.debug("No splitting documents into node chunks prior to embedding...")
                pipeline = IngestionPipeline(
                    transformations=[
                        self.embed_model,
                    ],
                    vector_store=self.vector_store,
                    docstore=SimpleDocumentStore(),
                )

        return pipeline

    def embed_documents(
        self,
        documents: Sequence[Document | LlamaDocument],
        extra_metadata_fields: dict | None = None,
        split_into_nodes: bool = True,  # type: ignore
    ):
        """ """
        if not documents:  # Check if the list is empty
            msg = "No documents provided to embed"
            raise ValueError(msg)

        first_doc = documents[0]

        if isinstance(first_doc, Document):
            logger.info("Embedding documents using LangChain...")
            return self._embed_documents_from_langchain_docs(
                docs=documents,
                extra_metadata_fields=extra_metadata_fields,
                split_into_nodes=split_into_nodes,  # type: ignore
            )

        if isinstance(first_doc, LlamaDocument):
            logger.info("Embedding documents using LlamaIndex...")
            return self._embed_documents_from_llamaindex_docs(
                docs=documents,
                extra_metadata_fields=extra_metadata_fields,
                split_into_nodes=split_into_nodes,  # type: ignore
            )

        logger.error(
            f"Type {type(first_doc)}. Invalid document type provided. Must be either Document or LlamaDocument."
        )

        return None

    def _embed_documents_from_langchain_docs(
        self,
        docs: Sequence[Document],
        extra_metadata_fields: dict | None = None,
        split_into_nodes: bool = False,
    ):
        # Update metadata with extra fields if provided
        if extra_metadata_fields is not None:
            for doc in docs:
                doc.metadata.update(extra_metadata_fields)

        if split_into_nodes:
            # Split the text into sentences
            logger.info("Splitting text into chunks prior to embedding...")
            document_splitter = LangChainDocumentSplitter()
            tokenized_docs = document_splitter.split_document_by_recursive_char(docs)
            logger.info(f"Split {len(docs)} documents into {len(tokenized_docs)} chunks")
        else:
            tokenized_docs = docs

        # Add docs to the collection. Can also update and delete.
        logger.info(f"Embedding {len(tokenized_docs)} chunked documents in ChromaDB...")

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
                    ids=[
                        doc.get("id", str(uuid.uuid4())) for doc in doc_sublist
                    ],  # unique for each doc
                )

                logger.info(f"Added {len(doc_sublist)} documents to the collection")
                logger.debug("Sleeping for 60 seconds to avoid rate limiting...")
                time.sleep(60)  # Sleep for a minute to avoid rate limiting

        if self.embedder == EmbedderType.OLLAMA:
            self.collection.add(
                documents=[
                    doc.page_content for doc in tokenized_docs
                ],  # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
                metadatas=[doc.metadata for doc in tokenized_docs],  # filter on these!
                ids=[str(uuid.uuid4()) for doc in tokenized_docs],  # unique for each doc
            )

            logger.info(f"Added {len(tokenized_docs)} documents to the collection")

    def _embed_documents_from_llamaindex_docs(
        self,
        docs: Sequence[LlamaDocument],
        extra_metadata_fields: dict | None = None,
        split_into_nodes: bool = False,
    ):
        # Update metadata with extra fields if provided
        if extra_metadata_fields is not None:
            for doc in docs:
                doc.metadata.update(extra_metadata_fields)

        # Check for duplicates and remove them from the list of documents
        logger.debug("Checking for duplicate documents in the collection prior to embedding...")
        unique_docs = []
        for id, doc in enumerate(docs):
            existing_doc_id = self.document_exists(
                doc.metadata["file_name"], doc.metadata["file_hash"]
            )
            if existing_doc_id:
                logger.warning(
                    f"Document {doc.metadata['file_name']} already exists in the collection. Skipping..."
                )
            else:
                unique_docs.append(doc)

        if len(unique_docs) == 0:
            logger.info("All documents already exist in the collection. No new documents to embed.")
            return

        logger.debug(
            f"Total Documents to Embed: {len(unique_docs)} out of initially provided {len(docs)}"
        )

        # We must now delete the existing documents from the collection that we will re-embed, to avoid duplicates
        for doc in unique_docs:
            existing_doc_id = self.get_document_id_by_file_name(doc.metadata["file_name"])
            if existing_doc_id:
                self.delete_documents(existing_doc_id)
                logger.debug(
                    f"Deleted existing document {doc.metadata['file_name']} from the collection"
                )

        if split_into_nodes:
            # Split the text into sentences
            logger.info(
                "[LlamaIndex] Will split documents into node chunks prior to embedding in ChromaDB"
            )
            node_splitter = LangchainNodeParser(
                RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=20)
            )

            self.index = VectorStoreIndex.from_documents(
                unique_docs,
                storage_context=self.storage_context,
                embed_model=self.embed_model,
                transformations=[node_splitter],
            )

        else:
            logger.info("[LlamaIndex] Embedding documents in ChromaDB without node parsing")
            self.index = VectorStoreIndex.from_documents(
                unique_docs, storage_context=self.storage_context, embed_model=self.embed_model
            )

        # Add docs to the collection. Can also update and delete.
        logger.info(f"[LlamaIndex] Embedded {len(unique_docs)} documents in ChromaDB...")

    def query_collection(
        self,
        query: list[str] | str,  # type: ignore
        filter: dict | None = None,  # type: ignore
        engine: Literal["LlamaIndex", "ChromaDB"] | None = None,  # type: ignore
        top_k: int = 5,
        metadata_only: bool = False,
    ) -> list | str:  # type: ignore
        """Queries the collection and retrieves relevant documents or metadata.

        This method allows you to query the collection using either LlamaIndex or ChromaDB
        as the query engine. You can provide a text query and optionally apply filters
        to refine the search.

        Args:
            query: The query text or a list of query texts.
            filter: A dictionary specifying filter conditions for ChromaDB (see ChromaDB documentation for filter syntax).
            engine: The query engine to use ("LlamaIndex" or "ChromaDB"). If None, the default engine will be used.
            top_k: The number of top results to return.
            metadata_only: If True, only the metadata of the retrieved documents will be returned.

        Returns:
            A list of retrieved documents or metadata, or a concatenated string of results if metadata_only is False.
        """

        if engine is None:
            engine = "ChromaDB"  # Set default if None

        if engine.lower() == "llamaindex":
            if not hasattr(self, "index"):
                logger.warning(
                    "No LlamaIndex retriever instance found. Initiating LlamaIndex ChromaDB Retriever."
                )
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store, embed_model=self.embed_model
                )

            # Are there any metadata filters to apply?
            if filter is None:
                filters = None
            else:
                filters_list = [
                    MetadataFilter(key=key, value=value) for key, value in filter.items()
                ]
                filters = MetadataFilters(filters=filters_list, condition=FilterCondition.AND)

            retriever = self.index.as_retriever(similarity_top_k=top_k, filters=filters)
            nodes = retriever.retrieve(query)

        elif engine.lower() == "chromadb":
            if isinstance(query, str):  # Check if it's a single string
                query = [query]  # Convert to a list for consistent handling

            if metadata_only:
                nodes = self.collection.query(
                    query_texts=query, where=filter, n_results=top_k, include=["metadatas"]
                )
            else:
                nodes = self.collection.query(query_texts=query, where=filter, n_results=top_k)

        else:
            logger.error(
                f"Invalid engine type {engine}. Please specify either 'LlamaIndex' or 'ChromaDB'"
            )

        return nodes

    def get_document_id_by_file_name(self, file_name: str) -> list | None:
        """Checks if a document with the given file_name and file_hash exists in the collection.

        Args:
            file_name: The name of the file.
            file_hash: The hash of the file.

        Returns:
            The document ID if a match is found, None otherwise.
        """
        filter = {"file_name": file_name}

        results = self.collection.get(where=filter, include=["metadatas"])

        if results and results["metadatas"]:
            return results.get("ids", None)

        return None

    def document_exists(self, file_name: str, file_hash: str) -> list | None:
        """Checks if a document with the given file_name and file_hash exists in the collection.

        Args:
            file_name: The name of the file.
            file_hash: The hash of the file.

        Returns:
            The document ID if a match is found, None otherwise.
        """
        filter = {
            "$and": [
                {"file_name": file_name},
                {"file_hash": file_hash},
            ]
        }

        results = self.collection.get(where=filter, include=["metadatas"])

        if results and results["metadatas"]:
            return results.get("ids", None)

        return None

    def delete_documents(self, document_ids: list[str]) -> None:
        """Deletes documents from the collection by their IDs.

        Args:
            document_ids: A list of document IDs to delete.
        """

        if not document_ids:
            logger.error("No document IDs provided for deletion.")
            return

        self.collection.delete(ids=document_ids)

        logger.debug(f"Deleted documents with IDs: {document_ids}")

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
