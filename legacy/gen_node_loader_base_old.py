# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
import json
import os
from pathlib import Path

import kuzu
from box import Box
from llama_index.core import Document, SimpleDirectoryReader
from loguru import logger

from ragintel.binders.archivers.chroma import ChromaOps
from ragintel.binders.loaders.github import GitHubLoader
from ragintel.binders.helpers.adaptors.pydantic import PydanticAdaptor
from ragintel.binders.helpers.adaptors.llamaindex import LlamaIndexDocDedup
from ragintel.binders.helpers.fileops import DirectoryManager
from ragintel.binders.helpers.enums import EmbedderType
from ragintel.binders.helpers.fileops import FileLoader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core.node_parser import LangchainNodeParser
from llama_index.core import VectorStoreIndex


class GenericFileLoader:
    def __init__(self, source_config: Box) -> None:
        logger.info(f"Initializing GenericFileLoader with config: {source_config}")

        self.directory_manager = DirectoryManager()

        # Initialize GitHub Loader for handy use of some functions
        self.ghloader = GitHubLoader()
        self.file_loader = FileLoader()

        # Extract Node Schema from Config so the variables can be referenced later if required
        self.repo_url = source_config.repo_url
        self.file_include_filter = source_config.file_include_filter
        self.file_exclude_filter = source_config.file_exclude_filter
        self.folder_exclude_list = source_config.folder_exclude_list
        self.node_schema = source_config.node_schema
        self.vector_collection = source_config.vector_collection
        self.graph_collection = source_config.graph_collection

        # Extract Directory Information from Config
        self.repo_name = self.ghloader.find_repo_name(source_config.repo_url)
        dest_directory = f"data/{self.repo_name}"
        self.dest_clone_directory = Path(dest_directory)

    def load_nodes(
        self,
        file_paths: list[str] | None = None,
        clone_repo: bool = True,
        load_to_graph: bool = True,
        load_to_vector: bool = True,
        embedder: str = "chroma",
        sample_only: bool = False,
    ) -> list[Document] | None:
        # Check if we need to clone the repository listed in the config
        if clone_repo:
            # Clone the Repository
            self.ghloader.clone_repository(
                self.repo_url, destination_folder=self.dest_clone_directory
            )  # type: ignore
        else:
            logger.info("Skipped repository cloning")

        # Check if we need to generate a list of files from the cloned repository
        if file_paths is None or []:
            logger.info("No list of files provided. Obtaining list from config.")
            # Grab list of rules files from directory where repo was cloned to
            excluded_files = self.file_exclude_filter or []
            excluded_folders = self.folder_exclude_list or []
            self.rules_file_list = self.file_loader.list_directory_recursive(
                self.dest_clone_directory,
                glob_patterns=self.file_include_filter,
                excluded_folders=excluded_folders,
                excluded_files=excluded_files,
                sample_only=sample_only,
            )
        else:
            self.rules_file_list = file_paths

        if self.rules_file_list == []:
            logger.error("No list of files provided. Exiting.")
            raise ValueError("No list of files provided. Exiting.")

        # Check if we only want to do a sample run
        if sample_only:
            logger.info("Sampling only 10 documents for testing purposes")
            load_file_limit = 10
        else:
            load_file_limit = 0  # Load all files

        # Load files into Document Objects

        # Load documents from the rules files using LlamaIndex, append file name and relative path of the file to the metadata
        def _get_llamaindex_file_metadata(file_name):
            file_name_leaf = Path(file_name).name
            relative_path = Path(file_name)
            file_hash = self.file_loader.get_file_hash(file_name)
            doc_url = self.ghloader.find_repo_url(relative_path, self.repo_url)  # type: ignore

            meta_properties = {
                "file_name": file_name_leaf,
                "relative_path": str(relative_path),
                "file_hash": file_hash,
                "doc_url": doc_url,
            }

            return meta_properties

        documents = SimpleDirectoryReader(
            input_files=self.rules_file_list,
            file_metadata=_get_llamaindex_file_metadata,
            num_files_limit=load_file_limit,
        ).load_data()

        logger.info(f"Loaded {len(documents)} documents from {len(self.rules_file_list)} files")

        # Load rules into GraphDB and VectorDB
        if load_to_graph or load_to_vector:
            if load_to_graph:
                self.load_rules_to_graph(documents=documents)

            if load_to_vector:
                try:
                    self.load_rules_to_vector_store(documents=documents, embedder=embedder)
                except Exception as e:
                    logger.error(f"Error loading files to ChromaDB: {e}")

        else:
            logger.info("Skipping loading to Graph and ChromaDB")
            return documents

    def load_rules_to_graph(
        self,
        documents: list[Document],
    ) -> None:
        """
        Loads rules into Kuzu Graph Database.

        Args:
            file_paths (list[str] | None): A list of file paths. If None, the function will clone a repository and use the cloned files. Default is None.
            load_to_vector (bool): Whether to load the files into ChromaDB for embedding and querying. Default is False.
            embedder (str): The type of text embedder to use. Default is "chroma".

        Returns:
            None

        This function creates a schema for rules in the database and loads rules from YAML files into the database.

        Raises:
            None
        """

        # TODO: Implement GraphDB abstraction layer that can be used to load rules into any GraphDB

        # Create an empty KuzuDB on-disk database and connect to it
        db = kuzu.Database(os.getenv("KUZU_DB_PERSIST_DIRECTORY", "./data/raginteldb"))
        self.conn = kuzu.Connection(db)

        # Create KuzuDB Schema
        # Start by retrieving from Pydantic the schema for SigmaNode
        GenFileNodeSchema = PydanticAdaptor()
        logger.info("Creating or Getting Node Schema in KuzuDB")
        self.conn.execute(f"""
            CREATE NODE TABLE IF NOT EXISTS {self.graph_collection}(
            {GenFileNodeSchema.pydantic_to_schema_string(self.node_schema)}
            )
        """)

        processed_docs = []

        # Process documents using LlamaIndex
        for doc in documents:
            try:
                if doc.metadata.get("relative_path") not in processed_docs:
                    logger.debug(f"Loading Node: {doc.metadata['relative_path']}")

                    processed_docs.append(doc.metadata.get("relative_path"))

                    node_type = "detection"
                    node_subtype = "GenFileNode"
                    source_url = doc.metadata.get("doc_url", "NA")
                    title = doc.metadata.get("file_name", "NA")
                    id = doc.metadata.get("file_name", "NA")
                    file_hash = doc.metadata.get("file_hash", "NA")
                    raw_document = self.file_loader.load_and_escape_raw_file_content_for_graph_db(
                        doc.metadata.get("relative_path")
                    )  # type: ignore

                    self.conn.execute(f"""
                        CREATE (s:{self.graph_collection} {{
                            node_type: "{node_type}",
                            node_subtype: "{node_subtype}",
                            source_url: "{source_url}",
                            title: "{title}",
                            id: "{id}",
                            file_hash: "{file_hash}",
                            raw_document: {raw_document}
                        }})
                    """)

            except Exception as e:
                if "Found duplicated primary key value" in str(e):
                    logger.warning(
                        f"Found duplicated primary key value: {doc.metadata.get('file_hash')}. Skipping."
                    )
                else:
                    logger.error(f"Error loading File: {e}. Continuing to next file.")
                continue

        logger.info("Finished loading Rules to GraphDB")

    def load_rules_to_vector_store(
        self, documents: list[Document], embedder: str = "chroma"
    ) -> None:
        """
        Loads rules into ChromaDB.
        """

        # Create a connection to the ChromaDB Ops class for embedding
        chroma_conn = ChromaOps(
            embedder=EmbedderType[embedder.upper()],
            collection_name=os.getenv("CHROMA_DB_DETECTIONS_COLLECTION", "detections"),
        )
        chroma_conn.embed_documents(documents)
