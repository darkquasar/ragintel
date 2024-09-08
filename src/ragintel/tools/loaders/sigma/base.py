# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
import json
import os
import uuid
from pathlib import Path, PurePosixPath

import kuzu
import yaml
from langchain.docstore.document import Document
from langchain_community.document_loaders import DirectoryLoader
from loguru import logger

from ragintel.nodes.detections import SigmaNode
from ragintel.tools.archivers.chroma import ChromaOps
from ragintel.tools.loaders.github import GitHubLoader
from ragintel.utils.adaptors.pydantic import PydanticAdaptor
from ragintel.utils.directory_manager import DirectoryManager
from ragintel.utils.enums import EmbedderType
from ragintel.utils.file_loader import FileLoader


class SigmaLoader:
    def __init__(self):
        # Create an empty on-disk database and connect to it
        db = kuzu.Database("./data/ragintel.db")
        self.conn = kuzu.Connection(db)
        self.sigma_file_list = []
        self.directory_manager = DirectoryManager()
        self.sigma_dest_directory = Path("./data/sigma")

    def clone_sigma_repo(
        self, repo_path: str = "SigmaHQ/sigma", dest_directory: str = "./data/sigma"
    ) -> None:
        """
        Clones a Sigma repository from GitHub.

        :param repo_url: str, the URL of the Sigma repository to clone.
        :param repo_path: str, the path to clone the repository to.
        :return: None

        This function clones a Sigma repository from GitHub using the GitHubLoader class.

        Raises:
        - None
        """

        # This will override the default set by the __init__ method if someone chooses to provide a different path
        self.sigma_dest_directory = Path(dest_directory)
        self.directory_manager.create_directory(self.sigma_dest_directory)

        # Clone the Sigma repository
        ghloader = GitHubLoader()
        ghloader.clone_repository(repo_path, destination_folder=self.sigma_dest_directory)
        logger.info(f"Cloned Sigma repository to {self.sigma_dest_directory}")

        logger.info("Deleting unnecessary directories from Sigma repository")
        dm = DirectoryManager()
        dm.delete_directory(
            [
                "data/sigma/tests/",
                "data/sigma/unsupported/",
                "data/sigma/.github/",
                "data/sigma/deprecated/",
                "data/sigma/other/",
                "data/sigma/documentation/",
                "data/sigma/images/",
            ],
            whatif=False,
        )

    def load_rules_to_graph(
        self,
        file_paths: list[str] | None = None,
        clone_repo: bool = True,
        load_to_chroma: bool = False,
        chroma_embedder: str = "chroma",
        sample_only: bool = False,
    ) -> list[Document] | None:
        """
        Loads Sigma rules into Kuzu Graph Database.

        Args:
            file_paths (list[str] | None): A list of file paths to Sigma rules YAML files. If None, the function will clone a Sigma repository and use the cloned files. Default is None.
            load_to_chroma (bool): Whether to load the Sigma rules into ChromaDB for embedding and querying. Default is False.
            chroma_embedder (str): The type of embedder to use for ChromaDB. Default is "chroma".

        Returns:
            None

        This function creates a schema for Sigma rules in the database and loads Sigma rules from YAML files into the database.

        Raises:
            None
        """
        if clone_repo:
            self.clone_sigma_repo()

        # Grab list of Sigma rules files
        FileLoad = FileLoader()
        exclude_files = [".github", "deprecated", "other", "unsupported", "tests", "test"]
        self.sigma_file_list = FileLoad.list_directory_recursive(
            str(self.sigma_dest_directory), "*.yml", exclude_patterns=exclude_files
        )

        if file_paths is None:
            file_paths = []

        if self.sigma_file_list != []:
            logger.info(
                f"Found {len(self.sigma_file_list)} Sigma rules files based on recent repo cloning."
            )
            file_paths = self.sigma_file_list
        else:
            logger.warning(
                "No defined list of sigma rules files based on recent repo cloning. Resorting to user provided list of sigma rules files."
            )
            if file_paths == []:
                logger.error("No list of sigma rules files provided. Exiting.")
                return

        # Check if we only want to do a sample run
        if sample_only:
            logger.info("Sampling only 5 Sigma rules for testing purposes")
            file_paths = file_paths[:5]

        # Create KuzuDB Schema
        # Start by retrieving from Pydantic the schema for SigmaNode
        SigmaNodeSchema = PydanticAdaptor()
        self.conn.execute(f"""
            CREATE NODE TABLE IF NOT EXISTS SigmaRule(
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
                base_url = "https://github.com/SigmaHQ/sigma/blob/master/"
                # fmt: off
                try:
                    # Find the index of "rules/" in the path parts
                    parts = file_path.parts
                    sigma_index = parts.index("sigma")
                    # Join the parts from "rules/" onwards
                    relative_path = PurePosixPath(*parts[sigma_index + 1:])
                    # Join the base URL and the relative path
                    full_url = base_url + str(relative_path)
                except ValueError:
                    logger.error(f"Could not find 'rules/' in path: {file_path}")
                # fmt: on
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

                self.conn.execute(f"""
                    CREATE (s:SigmaRule {{
                        node_type: "detection",
                        node_subtype: "sigma",
                        source_url: "{full_url}",
                        title: {json.dumps(sigma_rule_data.get('title', 'NA'))},
                        id: "{sigma_rule_data.get('id', 'NA')}",
                        status: "{sigma_rule_data.get('status', 'NA')}",
                        description: {json.dumps(sigma_rule_data.get('description', 'NA'))},
                        references: {sigma_rule_data.get('references', ['NA'])},
                        author: {json.dumps(sigma_rule_data.get('author', 'NA'))},
                        date: "{sigma_rule_data.get('date', 'NA')}",
                        modified: "{sigma_rule_data.get('modified', 'NA')}",
                        tags: {sigma_rule_data.get('tags', ['NA'])},
                        logsource: {json.dumps(sigma_rule_data.get('logsource', ['NA']))},
                        detection: {json.dumps(sigma_rule_data.get('detection', ['NA']))},
                        falsepositives: {sigma_rule_data.get('falsepositives', ['NA'])},
                        level: {json.dumps(sigma_rule_data.get('level', 'NA'))},
                        raw_document: {json.dumps(yaml_string)}
                    }})
                """)
            except Exception as e:
                logger.error(f"Error loading Sigma rule: {e}. Continuing to next rule.")
                continue

        logger.info("Finished loading Sigma rules to KuzuDB")

        if load_to_chroma:
            try:
                self.load_rules_to_vector_store(
                    embedder=chroma_embedder, sigma_folder_path=self.sigma_dest_directory
                )
            except Exception as e:
                logger.error(
                    f"Error loading Sigma rules to ChromaDB: {e}. Continuing to next rule."
                )

    def load_rules_to_vector_store(
        self,
        embedder: str = "chroma",
        sigma_folder_path: str = "data/sigma",
        rule_quantity: int = 300,
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

        # Let's use Langchain's DirectoryLoader to load Sigma rules into Document Objects
        logger.info("Loading Sigma rules Document Objects")
        loader = DirectoryLoader(
            sigma_folder_path,
            glob="**/*.yml",
            use_multithreading=False,
            recursive=True,
            show_progress=True,
            sample_size=rule_quantity,
            exclude=[
                "**/.github/**",
                "**/deprecated/**",
                "*deprecated*",
                "**/other/**",
                "*test*",
                "**/unsupported/**",
            ],
        )
        docs = loader.load()
        logger.info("Finished loading Sigma rules Document Objects")

        for doc in docs:
            file_path = Path(doc.metadata["source"])
            try:
                # Let's append necessary metadata for each document
                # Chromadb "medatadas" field is a dictionary that doesn't accept nested lists, so we need to convert the list of tags to a string of comma separated values
                with open(file_path) as f:
                    sigma_rule_data = yaml.safe_load(f)
                    logger.debug(
                        f"Fixing Metadata for Document: {sigma_rule_data.get('title', 'NA')}"
                    )
                    doc.metadata["id"] = sigma_rule_data.get("id", str(uuid.uuid4()))
                    doc.metadata["title"] = sigma_rule_data.get("title", "NA")
                    doc.metadata["tags"] = ", ".join(sigma_rule_data.get("tags", ["NA"]))

            except Exception as e:
                logger.error(f"Error editing Document: {e}. Continuing to next rule.")
                continue

        chroma_conn = ChromaOps(
            embedder=EmbedderType[embedder.upper()],
            collection_name=os.getenv("CHROMA_DB_DETECTIONS_COLLECTION", "detections"),
        )
        chroma_conn.embed_documents(docs)

        return

    def query_sigma_rules(self, cypher_query: str) -> list:
        """
        Queries the database for Sigma rules.

        :param query: str, the query to search for in the database.
        :return: List, a list of Sigma rules that match the query.

        This function queries the database for Sigma rules that match the provided query.

        Raises:
        - None
        """

        cypher_query = cypher_query.lower()
        return self.conn.execute(cypher_query)
