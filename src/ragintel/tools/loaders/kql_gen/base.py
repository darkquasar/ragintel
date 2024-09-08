# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
import json
import os
import re
from pathlib import Path

import kuzu
from box import Box
from llama_index.core import Document, SimpleDirectoryReader
from loguru import logger

from ragintel.tools.archivers.chroma import ChromaOps
from ragintel.tools.loaders.github import GitHubLoader
from ragintel.utils.adaptors.pydantic import PydanticAdaptor
from ragintel.utils.base.llamaindex_doc_dedup import LlamaIndexDocDedup
from ragintel.utils.directory_manager import DirectoryManager
from ragintel.utils.enums import EmbedderType
from ragintel.utils.file_loader import FileLoader


class KQLLoader:
    def __init__(self, source_config: Box) -> None:
        logger.info(f"Initializing KQLLoader with config: {source_config}")

        self.directory_manager = DirectoryManager()

        # Initialize GitHub Loader for handy use of some functions
        self.ghloader = GitHubLoader()

        # Extract Node Schema from Config so the variables can be referenced later if required
        self.repo_url = source_config.repo_url
        self.file_include_filter = source_config.file_include_filter
        self.file_exclude_filter = source_config.file_exclude_filter
        self.folder_exclude_list = source_config.folder_exclude_list
        self.node_schema = source_config.node_schema

        # Extract Directory Information from Config
        self.repo_name = self.ghloader.find_repo_name(source_config.repo_url)
        dest_directory = f"data/{self.repo_name}"
        self.dest_clone_directory = Path(dest_directory)

    def clone_repo(
        self,
        repo_url: str | None = None,
        dest_directory: str | None = None,
        delete_folders: list[str] | None = None,
    ) -> None:
        """
        Clones a Detection repository from GitHub.

        :param repo_url: str, the URL of the repository to clone.
        :param repo_path: str, the path to clone the repository to.
        :return: None

        This function clones a repository from GitHub using the GitHubLoader class.

        Raises:
        - None
        """

        # This will override the default set by the __init__ method if someone chooses to provide a different path
        if dest_directory is not None:
            self.dest_clone_directory = Path(dest_directory)

        # Clone the Repository
        self.ghloader.clone_repository(self.repo_url, destination_folder=self.dest_clone_directory)
        logger.info(f"Cloned Repository to {self.dest_clone_directory.absolute()}")

        if delete_folders is not None:
            logger.info("Deleting unnecessary directories from cloned Repository")
            dm = DirectoryManager()
            dm.delete_directory(delete_folders, whatif=False)

    def load_rules_to_graph(
        self,
        file_paths: list[str] | None = None,
        clone_repo: bool = True,
        load_to_chroma: bool = False,
        chroma_embedder: str = "chroma",
        sample_only: bool = False,
    ) -> list[Document] | None:
        """
        Loads rules into Kuzu Graph Database.

        Args:
            file_paths (list[str] | None): A list of file paths to rules files. If None, the function will clone a repository and use the cloned files. Default is None.
            load_to_chroma (bool): Whether to load the rules into ChromaDB for embedding and querying. Default is False.
            chroma_embedder (str): The type of embedder to use for ChromaDB. Default is "chroma".

        Returns:
            None

        This function creates a schema for rules in the database and loads rules from YAML files into the database.

        Raises:
            None
        """
        if clone_repo:
            self.clone_repo()

        # Grab list of rules files from directory where repo was cloned to
        FileLoad = FileLoader()
        excluded_files = self.file_exclude_filter or []
        excluded_folders = self.folder_exclude_list or []
        excluded_files_list = excluded_files + excluded_folders
        self.rules_file_list = FileLoad.list_directory_recursive(
            str(self.dest_clone_directory),
            glob_patterns=self.file_include_filter,
            exclude_patterns=excluded_files_list,
            sample_only=sample_only,
        )

        if file_paths is None:
            file_paths = []

        if self.rules_file_list != []:
            logger.info(
                f"Found {len(self.rules_file_list)} Rules files based on recent repo cloning."
            )
            file_paths = self.rules_file_list
        else:
            logger.warning(
                "No defined list of rules files based on recent repo cloning. Resorting to user provided list of rules files."
            )
            if file_paths == []:
                logger.error("No list of rules files provided. Exiting.")
                return None

        # Create an empty KuzuDB on-disk database and connect to it
        db = kuzu.Database(os.getenv("KUZU_DB_PERSIST_DIRECTORY", "./data/raginteldb"))
        self.conn = kuzu.Connection(db)

        # Create KuzuDB Schema
        # Start by retrieving from Pydantic the schema for SigmaNode
        KQLNodeSchema = PydanticAdaptor()
        logger.info("Creating or Getting KQLRule Schema in KuzuDB")
        self.conn.execute(f"""
            CREATE NODE TABLE IF NOT EXISTS KQLRule(
            {KQLNodeSchema.pydantic_to_schema_string(self.node_schema)}
            )
        """)

        # Check if we only want to do a sample run
        if sample_only:
            logger.info("Sampling only 5 rules for testing purposes")
            load_file_limit = 5
        else:
            load_file_limit = None

        # Load documents from the rules files using LlamaIndex, append file name and relative path of the file to the metadata
        def filename_fn(file_name):
            return {"file_name": Path(file_name).name, "relative_path": str(Path(file_name))}

        documents = SimpleDirectoryReader(
            input_files=self.rules_file_list,
            file_metadata=filename_fn,
            num_files_limit=load_file_limit,
        ).load_data()

        # LlamaIndex might chunk documents loaded via SimpleDirectoryReader, we need to create a deduplicated list that we can use to load into KuzuDB because we want to load the raw content of the file only once. The original list of Documents from LlamaIndex remains the same, because we will later use that to load into a Vector Database where the chunks are going to be useful.
        dedup_doc_list = LlamaIndexDocDedup().deduplicate_documents(documents)
        dedup_doc_relative_paths = [doc["relative_path"] for doc in dedup_doc_list]
        dedup_doc_hashes = [doc["doc_hash"] for doc in dedup_doc_list]
        processed_docs = []

        # Process documents using LlamaIndex
        for doc in documents:
            try:
                if doc.metadata.get("relative_path") not in processed_docs:
                    processed_docs.append(doc.metadata.get("relative_path"))
                    doc_relative_path_index = dedup_doc_relative_paths.index(
                        doc.metadata.get("relative_path")
                    )

                    with open(doc.metadata.get("relative_path")) as f:
                        doc_content = f.read()

                    # Grab URL value for the rule too
                    doc.metadata["doc_url"] = self.ghloader.find_repo_url(
                        doc.metadata["relative_path"], self.repo_url
                    )

                    logger.debug(f"Loading Rule: {doc.metadata['relative_path']}")

                    title = json.dumps(doc.metadata["relative_path"].rsplit("\\", 1)[-1])
                    raw_document = json.dumps(
                        re.sub(r"[\n\r]", lambda match: "\\\\" + match.group(0), doc_content)
                    )

                    self.conn.execute(f"""
                        CREATE (s:KQLRule {{
                            node_type: "detection",
                            node_subtype: "kql",
                            source_url: "{doc.metadata["doc_url"]}",
                            title: {title},
                            id: "{dedup_doc_hashes[doc_relative_path_index]}",
                            raw_document: {raw_document}
                        }})
                    """)

            except Exception as e:
                logger.error(f"Error loading Rule: {e}. Continuing to next rule.")
                continue

        self.conn.close()
        logger.info("Finished loading Rules to KuzuDB")

        if load_to_chroma:
            try:
                self.load_rules_to_vector_store(documents=documents, embedder=chroma_embedder)
            except Exception as e:
                logger.error(f"Error loading Rules to ChromaDB: {e}. Continuing to next rule.")

        # Return documents if sample_only is True
        if sample_only:
            logger.info("Sample run completed. Returning collection of docs for examination.")
            return documents

        return None

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

    def query_graph(self, cypher_query: str) -> list:
        """ """

        cypher_query = cypher_query.lower()
        return self.conn.execute(cypher_query)
