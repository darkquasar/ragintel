import json
import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import kuzu
from box import Box
from langchain.docstore.document import Document as LangchainDocument
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from llama_index.core import Document, SimpleDirectoryReader
from loguru import logger
from pydantic._internal._model_construction import ModelMetaclass

from ragintel.binders.archivers.chroma import ChromaOps
from ragintel.binders.helpers.adaptors.pydantic import PydanticAdaptor
from ragintel.binders.helpers.enums import EmbedderType
from ragintel.binders.helpers.fileops import DirectoryManager, FileLoader
from ragintel.binders.loaders.github import GitHubLoader


class BaseNodeLoader:
    """
    Base class for loading data from various sources.
    Handles common operations like cloning repos, listing files,
    and basic data extraction.
    """

    def __init__(self, source_config: Box) -> None:
        logger.info(f"Initializing BaseLoader with config: {source_config}")

        self.directory_manager = DirectoryManager()
        self.ghloader = GitHubLoader()
        self.file_loader = FileLoader()

        self.vector_collection = source_config.vector_collection
        self.graph_collection = source_config.graph_collection
        self.repo_url = source_config.repo_url
        self.file_include_filter = source_config.file_include_filter
        self.file_exclude_filter = source_config.file_exclude_filter
        self.folder_exclude_list = source_config.folder_exclude_list
        self.node_schema = source_config.node_schema

        # Extract some Directory Information from Config
        self.repo_name = self.ghloader.find_repo_name(source_config.repo_url)
        dest_directory = f"data/{self.repo_name}"
        self.dest_clone_directory = Path(dest_directory)

    def _clone_repo(self):
        """Clones the configured repository."""
        self.ghloader.clone_repository(self.repo_url, destination_folder=self.dest_clone_directory)  # type: ignore

    def load_and_escape_raw_file_content_for_graph_db(self, relative_path: str) -> str:
        """Loads and escapes raw file content for graph database."""
        doc = self.file_loader.load_and_escape_raw_file_content_for_graph_db(relative_path)
        return doc

    def _get_file_list(
        self, file_paths: list[str] | None = None, sample_only: bool = False
    ) -> list[str]:
        """Returns a list of files to process."""
        if file_paths is None or []:
            logger.info("No list of files provided. Obtaining list from config.")
            excluded_files = self.file_exclude_filter or []
            excluded_folders = self.folder_exclude_list or []
            self.files_list = self.file_loader.list_directory_recursive(
                self.dest_clone_directory,
                glob_patterns=self.file_include_filter,
                excluded_folders=excluded_folders,
                excluded_files=excluded_files,
                sample_only=sample_only,
            )

            self.files_list = [str(file) for file in self.files_list]

            return self.files_list
        return file_paths

    def load_documents_from_file_list_with_llamaindex(
        self, file_paths: list[str], sample_only: bool = False
    ) -> list[Document]:
        """Loads files into LlamaIndex Document objects."""

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

        load_file_limit = 10 if sample_only else 0  # Load all files if not sampling

        self.documents = SimpleDirectoryReader(
            input_files=file_paths,
            file_metadata=_get_llamaindex_file_metadata,
            num_files_limit=load_file_limit,
        ).load_data()

        return self.documents

    def load_documents_from_file_list_with_langchain(
        self,
        folder_exclude_list: list[str] = [],
        sample_only: bool = False,
        convert_to_llamaindex_document: bool = True,
    ) -> Sequence[LangchainDocument] | Sequence[Document]:
        """Loads files into Langchain Document objects."""

        # Check if we only want to do a sample run
        if sample_only:
            logger.info("Sampling only 10 Sigma rules for testing purposes")
            rule_quantity = 10
        else:
            rule_quantity = 0  # Load all rules

        # First let's obtain a proper list of all the excluded folders, because Langchain's DirectoryLoader
        # uses pathlib Path.match() method to exclude folders, which does not support recursive exclusion
        if folder_exclude_list not in [None, []]:
            self.folder_exclude_list = folder_exclude_list
        directory_excludes = self.file_loader.find_exclusion_folders(
            self.folder_exclude_list, str(self.dest_clone_directory), return_glob_pattern=True
        )

        # Let's use Langchain's DirectoryLoader to load Sigma rules into Document Objects
        logger.info("Loading Sigma rules Document Objects")
        loader = DirectoryLoader(
            str(self.dest_clone_directory),
            glob=self.file_include_filter,
            loader_cls=TextLoader,
            use_multithreading=False,
            recursive=True,
            show_progress=True,
            sample_size=rule_quantity,
            exclude=directory_excludes,
        )

        self.documents = loader.load()

        for doc in self.documents:
            self._expand_langchain_document_metadata(doc)

        if convert_to_llamaindex_document:
            # Convert Langchain Document to LlamaIndex Document
            logger.info("Converting Langchain Documents to LlamaIndex Documents")
            self.documents = [Document.from_langchain_format(doc) for doc in self.documents]

        logger.info("Finished loading Sigma rules Document Objects")

        return self.documents

    def _escape_list_and_return_string(self, data_list: list) -> list[str]:
        return [json.dumps(value).strip('"') for value in data_list]

    def _escape_string(self, data: str) -> str:
        return json.dumps(data).strip('"')

    def _convert_date_to_string(self, date_data: date | str) -> str:
        """Converts a date object to a string."""

        if isinstance(date_data, str):
            return date_data

        return date_data.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD

    def _expand_langchain_document_metadata(self, document: LangchainDocument) -> LangchainDocument:
        file_path = Path(document.metadata["source"])

        try:
            # Let's append necessary metadata for each document
            # Chromadb "medatadas" field is a dictionary that doesn't accept nested lists, so we need to convert the list of tags to a string of comma separated values

            # Grab file hash for id
            file_name = self.file_loader.get_file_name(file_path)  # type: ignore
            file_hash = self.file_loader.get_file_hash(file_path)
            doc_url = self.ghloader.find_repo_url(document.metadata["source"], self.repo_url)  # type: ignore

            # Calculate relative path relative to the destination clone directory
            try:
                relative_path = str(file_path.relative_to(self.dest_clone_directory))
            except ValueError:
                # If file_path is not relative to dest_clone_directory, use the file path as-is
                relative_path = str(file_path)

            logger.debug(f"Fixing Metadata for Document: {file_name}")
            document.metadata["id"] = file_name
            document.metadata["file_name"] = file_name
            document.metadata["file_hash"] = file_hash
            document.metadata["doc_url"] = doc_url
            document.metadata["relative_path"] = relative_path

        except Exception as e:
            logger.error(f"Error editing Document: {e}. Continuing to next file.")

        return document

    def _construct_kuzu_properties_str(self, pydantic_node) -> str:
        """
        Constructs the properties string for a Kuzu Cypher query from a dictionary.
        Handles type conversion for fields that should be arrays but contain single values.
        """
        data_dict = pydantic_node.model_dump()
        properties = []

        # Get the schema information to understand expected types
        schema_fields = self._get_schema_field_types(pydantic_node.__class__)

        for key, value in data_dict.items():
            expected_type = schema_fields.get(key, "STRING")

            if expected_type == "STRING[]":
                # This field should be an array
                if isinstance(value, list):
                    # Already a list, format as array
                    formatted_list = [f'"{item!s}"' for item in value]
                    properties.append(f"""{key}: [{", ".join(formatted_list)}]""")
                else:
                    # Single value, convert to single-element array
                    if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]  # Strip quotes if present
                    properties.append(f"""{key}: ["{value!s}"]""")
            else:
                # Regular field handling
                if not isinstance(value, list):
                    if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]  # Strip quotes if present
                    properties.append(f"""{key}: "{value}" """)
                else:
                    # This shouldn't happen for non-array fields, but handle gracefully
                    formatted_list = [f'"{item!s}"' for item in value]
                    properties.append(f"""{key}: [{", ".join(formatted_list)}]""")

        return ", ".join(properties)

    def _get_schema_field_types(self, model_class) -> dict:
        """
        Gets the expected KuzuDB types for each field in the Pydantic model.

        Args:
            model_class: The Pydantic model class

        Returns:
            Dictionary mapping field names to their KuzuDB types
        """
        adaptor = PydanticAdaptor()
        field_types = {}

        for field_name, field_info in model_class.model_fields.items():
            kuzu_type = adaptor._get_kuzu_type(field_name, field_info)
            field_types[field_name] = kuzu_type

        return field_types

    def get_llamaindex_doc_metadata(self, field, metadata: dict) -> str:
        """Extracts value from llamaindex metadata."""
        return metadata.get(field, "NA")

    def load_nodes_to_graphdb_llamaindex(
        self,
        documents: Sequence[Document],
        node_schema: ModelMetaclass,
    ) -> None:
        """
        Loads rules into Kuzu Graph Database.

        Args:
            documents (Sequence[Document]): A list of Document objects.

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
                # We try to avoid adding duplicate nodes to the graph
                if doc.metadata.get("relative_path") not in processed_docs:
                    logger.debug(f"Loading Node: {doc.metadata.get('relative_path')}")
                    processed_docs.append(doc.metadata.get("relative_path"))

                    # We cast the document metadata to the Pydantic schema
                    # The Pydantic schema has a Validator that will ensure the data is parsed correctly
                    # We need to pass in the current instance of the BaseNodeLoader to the Pydantic schema as "self"
                    data = node_schema(doc.metadata, self)

                    # We construct a Cypher query to insert the node into KuzuDB Graph
                    self.conn.execute(f"""
                    CREATE (s:{self.graph_collection} {{{self._construct_kuzu_properties_str(data)}}})
                    """)

                # We now need to delete the loader "key" from the document metadata to avoid conflicts in downstream processing
                if "loader" in doc.metadata:
                    del doc.metadata["loader"]

            except Exception as e:
                # We now need to delete the loader "key" from the document metadata to avoid conflicts in downstream processing
                if "loader" in doc.metadata:
                    del doc.metadata["loader"]
                if "Found duplicated primary key value" in str(e):
                    logger.warning(
                        f"Found duplicated primary key value: {doc.metadata.get('file_name')}. Skipping."
                    )
                else:
                    logger.error(f"Error loading File: {e}. Continuing to next file.")
                continue

        logger.info("Finished loading Rules to GraphDB")

    def load_nodes_to_vectordb_llamaindex(
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
