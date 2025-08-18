# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
import json
import os
import uuid
from collections.abc import Sequence
from pathlib import Path

import kuzu
import yaml
from box import Box
from langchain.docstore.document import Document
from langchain_community.document_loaders import DirectoryLoader
from loguru import logger

from ragintel.binders.archivers.chroma import ChromaOps
from ragintel.binders.helpers.adaptors.pydantic import PydanticAdaptor
from ragintel.binders.helpers.enums import EmbedderType
from ragintel.binders.helpers.fileops import FileLoader
from ragintel.binders.helpers.fileops.directory_manager import DirectoryManager
from ragintel.binders.loaders.github import GitHubLoader
from ragintel.nodes.detections import SigmaNode


class SigmaLoader:
    def __init__(self, source_config: Box) -> None:
        logger.info(f"Initializing SigmaLoader with config: {source_config}")

        self.directory_manager = DirectoryManager()

        # Initialize some Loaders for handy use of some functions
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
        file_paths: Sequence[str] | None = None,
        clone_repo: bool = True,
        load_to_graph: bool = True,
        load_to_vector: bool = True,
        embedder: str = "chroma",
        sample_only: bool = False,
    ) -> Sequence[Document] | None:
        # Check if we need to clone the repository listed in the config
        if clone_repo:
            # Clone the Repository
            self.ghloader.clone_repository(
                self.repo_url, destination_folder=self.dest_clone_directory
            )  # type: ignore
        else:
            logger.info("Skipping cloning repository")

        # Check if we need to generate a list of files from the cloned repository
        if file_paths is None or []:
            logger.info("No list of Sigma rules files provided. Obtaining lits from config.")
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
            logger.info("Sampling only 10 Sigma rules for testing purposes")
            rule_quantity = 10
        else:
            rule_quantity = 0  # Load all rules

        # Load files into Document Objects

        # First let's obtain a proper list of all the excluded folders, because Langchain's DirectoryLoader
        # uses pathlib Path.match() method to exclude folders, which does not support recursive exclusion
        directory_excludes = self.file_loader.find_exclusion_folders(
            self.folder_exclude_list, str(self.dest_clone_directory), return_glob_pattern=True
        )

        # Let's use Langchain's DirectoryLoader to load Sigma rules into Document Objects
        logger.info("Loading Sigma rules Document Objects")
        loader = DirectoryLoader(
            str(self.dest_clone_directory),
            glob=self.file_include_filter,
            use_multithreading=False,
            recursive=True,
            show_progress=True,
            sample_size=rule_quantity,
            exclude=directory_excludes,
        )
        documents = loader.load()
        logger.info("Finished loading Sigma rules Document Objects")
        # Let's split documents into nodes

        if load_to_graph or load_to_vector:
            if load_to_graph:
                self.load_rules_to_graph(
                    file_paths=self.rules_file_list,  # type: ignore
                )

            if load_to_vector:
                try:
                    self.load_rules_to_vector_store(documents=documents, embedder=embedder)
                except Exception as e:
                    logger.error(f"Error loading Sigma rules to ChromaDB: {e}")

        else:
            logger.info("Skipping loading to Graph and ChromaDB")
            return documents

    def load_rules_to_graph(
        self,
        file_paths: Sequence[str],
    ) -> None:
        """
        Loads Sigma rules into Kuzu Graph Database.

        :param file_paths: A list of file paths to Sigma rules YAML files. If None, the function will clone a Sigma repository and use the cloned files. Default is None.
        :type file_paths: list[str] | None
        :return: None

        This function creates a schema for Sigma rules in the database and loads Sigma rules from YAML files into the database.
        """

        # TODO: Implement GraphDB abstraction layer that can be used to load rules into any GraphDB

        # Create KuzuDB Schema
        # Start by retrieving from Pydantic the schema for SigmaNode
        SigmaNodeSchema = PydanticAdaptor()

        # Create an empty KuzuDB on-disk database and connect to it
        db = kuzu.Database(os.getenv("KUZU_DB_PERSIST_DIRECTORY", "./data/raginteldb"))
        self.conn = kuzu.Connection(db)
        self.conn.execute(f"""
            CREATE NODE TABLE IF NOT EXISTS {self.graph_collection}(
            {SigmaNodeSchema.pydantic_to_schema_string(SigmaNode)}
            )
        """)

        for file_path in file_paths:
            try:
                with open(file_path) as f:
                    sigma_rule_data = yaml.safe_load(f)

                # Convert back to YAML string so we can add it to "raw_document" field
                yaml_string = yaml.dump(sigma_rule_data)

                # Grab URL value for the rule too
                full_url = self.ghloader.find_repo_url(
                    Path(file_path),
                    self.repo_url,  # type: ignore
                )

                logger.debug(f"Loading Sigma rule: {sigma_rule_data['title']}")

                # Process the 'detection' field dynamically, storing results in a list of strings
                detection_data = []
                for selection_key, selection_value in sigma_rule_data["detection"].items():
                    if selection_key.startswith("selection_"):
                        if isinstance(selection_value, list):
                            # Handle the case where selection_value is a list
                            for item in selection_value:
                                if isinstance(item, dict):
                                    # If item is a dictionary, process it as before
                                    for field, value in item.items():
                                        if isinstance(value, list):
                                            detection_data.append(
                                                f"{selection_key}_{field}: {', '.join(value)}"
                                            )
                                        else:
                                            detection_data.append(
                                                f"{selection_key}_{field}: {value}"
                                            )
                                else:
                                    # If item is not a dictionary, handle it appropriately (e.g., append as is)
                                    detection_data.append(f"{selection_key}: {item}")
                        else:
                            # Handle the case where selection_value is a dictionary (as before)
                            for field, value in selection_value.items():
                                if isinstance(value, list):
                                    detection_data.append(
                                        f"{selection_key}_{field}: {', '.join(value)}"
                                    )
                                else:
                                    detection_data.append(f"{selection_key}_{field}: {value}")
                    else:
                        detection_data.append(f"{selection_key}: {selection_value}")

                # Process the 'logsource' attribute
                logsource_data = [
                    f"{key}: {value}" for key, value in sigma_rule_data["logsource"].items()
                ]

                # Update the sigma_rule_data with the processed logsource data
                sigma_rule_data["logsource"] = logsource_data
                # Update the sigma_rule_data with the processed detection data
                sigma_rule_data["detection"] = detection_data
                # Grab file hash for id
                file_hash = self.file_loader.get_file_hash(file_path)

                node_type = "detection"
                node_subtype = "sigma"
                source_url = full_url
                title = json.dumps(sigma_rule_data.get("title", "NA"))
                id = str(uuid.uuid4())
                sigma_id = sigma_rule_data.get("id", "NA")
                file_name = self.file_loader.get_file_name(file_path)
                file_hash = file_hash
                status = sigma_rule_data.get("status", "NA")
                description = json.dumps(sigma_rule_data.get("description", "NA"))
                references = sigma_rule_data.get("references", ["NA"])
                author = json.dumps(sigma_rule_data.get("author", "NA"))
                date = sigma_rule_data.get("date", "NA")
                modified = sigma_rule_data.get("modified", "NA")
                tags = sigma_rule_data.get("tags", ["NA"])
                logsource = json.dumps(sigma_rule_data.get("logsource", ["NA"]))
                detection = json.dumps(sigma_rule_data.get("detection", ["NA"]))
                falsepositives = sigma_rule_data.get("falsepositives", ["NA"])
                level = json.dumps(sigma_rule_data.get("level", "NA"))
                raw_document = json.dumps(yaml_string)

                self.conn.execute(f"""
                    CREATE (s:{self.graph_collection} {{
                        node_type: "{node_type}",
                        node_subtype: "{node_subtype}",
                        source_url: "{source_url}",
                        title: {title},
                        id: "{file_name}",
                        sigma_id: "{sigma_id}",
                        file_name: "{file_name}",
                        file_hash: "{file_hash}",
                        status: "{status}",
                        description: {description},
                        references: {references},
                        author: {author},
                        date: "{date}",
                        modified: "{modified}",
                        tags: {tags},
                        logsource: {logsource},
                        detection: {detection},
                        falsepositives: {falsepositives},
                        level: {level},
                        raw_document: {raw_document}
                    }})
                """)
            except Exception as e:
                logger.error(f"Error loading Sigma rule: {e}. Continuing to next rule.")
                continue

        logger.info("Finished loading Sigma rules to KuzuDB")

    def load_rules_to_vector_store(
        self,
        documents: Sequence[Document],
        embedder: str = "chroma",
    ) -> None:
        """
        Loads Sigma rules into ChromaDB.

        :param embedder: str, the type of embedder to use (default: "chroma").
        :param sigma_folder_path: str, the path to the Sigma rules folder (default: "data/sigma").
        :param rule_quantity: int, the number of rules to load (default: 300).
        :return: None

        This function loads Sigma rules into ChromaDB for embedding and querying.

        Raises:
        - None
        """

        for doc in documents:
            file_path = Path(doc.metadata["source"])
            try:
                # Let's append necessary metadata for each document
                # Chromadb "medatadas" field is a dictionary that doesn't accept nested lists, so we need to convert the list of tags to a string of comma separated values

                # Grab file hash for id
                file_name = self.file_loader.get_file_name(file_path)  # type: ignore
                file_hash = self.file_loader.get_file_hash(file_path)

                with open(file_path) as f:
                    sigma_rule_data = yaml.safe_load(f)
                    logger.debug(
                        f"Fixing Metadata for Document: {sigma_rule_data.get('title', 'NA')}"
                    )
                    doc.metadata["id"] = sigma_rule_data.get("id", "NA")
                    doc.metadata["file_name"] = file_name
                    doc.metadata["file_hash"] = file_hash
                    doc.metadata["title"] = sigma_rule_data.get("title", "NA")
                    doc.metadata["tags"] = ", ".join(sigma_rule_data.get("tags", ["NA"]))

            except Exception as e:
                logger.error(f"Error editing Document: {e}. Continuing to next rule.")
                continue

        chroma_conn = ChromaOps(
            embedder=EmbedderType[embedder.upper()],
            collection_name=os.getenv("CHROMA_DB_DETECTIONS_COLLECTION", "detections"),
        )
        chroma_conn.embed_documents(documents)

        return
