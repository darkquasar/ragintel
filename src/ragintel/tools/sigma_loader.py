# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
import json
import uuid
from pathlib import Path

import kuzu
import yaml
from langchain_community.document_loaders import DirectoryLoader
from loguru import logger

from ragintel.templates.enums import EmbedderType
from ragintel.tools.chromadb_tools import ChromaOps
from ragintel.tools.github_loader import GitHubLoader
from ragintel.utils.directory_manager import DirectoryManager
from ragintel.utils.file_loader import FileLoader


class SigmaLoader:
    def __init__(self):

        # Create an empty on-disk database and connect to it
        db = kuzu.Database("./data/ragintel.db")
        self.conn = kuzu.Connection(db)
        self.sigma_file_list = []
        self.directory_manager = DirectoryManager()

    def clone_sigma_repo(self, repo_path: str = "SigmaHQ/sigma") -> None:
        """
        Clones a Sigma repository from GitHub.

        :param repo_url: str, the URL of the Sigma repository to clone.
        :param repo_path: str, the path to clone the repository to.
        :return: None

        This function clones a Sigma repository from GitHub using the GitHubLoader class.

        Raises:
        - None
        """

        self.sigma_dest_directory = Path("./data/sigma")
        self.directory_manager.create_directory(self.sigma_dest_directory)

        # Clone the Sigma repository
        ghloader = GitHubLoader()
        ghloader.clone_repository(repo_path, destination_folder=self.sigma_dest_directory)
        logger.info(f"Cloned Sigma repository to {self.sigma_dest_directory}")

        logger.info("Deleting unnecessary directories from Sigma repository")
        dm = DirectoryManager()
        dm.delete_directory(["data/sigma/tests/", "data/sigma/unsupported/", "data/sigma/.github/", "data/sigma/deprecated/", "data/sigma/other/", "data/sigma/documentation/", "data/sigma/images/"])

        FileLoad = FileLoader()
        exclude_files = [".github", "deprecated", "other", "unsupported", "tests", "test"]
        self.sigma_file_list = FileLoad.list_directory_recursive(str(self.sigma_dest_directory), "*.yml", exclude_patterns=exclude_files)

    def load_sigma_rules(self, file_paths: list[str] = [], load_to_chroma: bool = False, chroma_embedder: str = "chroma") -> None:
        """
        Loads Sigma rules into Kuzu Graph Database.

        :param None:
        :return: None

        This function creates a schema for Sigma rules in the database and loads Sigma rules from YAML files into the database.

        Raises:
        - None
        """

        self.clone_sigma_repo()

        if self.sigma_file_list != []:
            logger.info(f"Found {len(self.sigma_file_list)} Sigma rules files based on recent repo cloning.")
            file_paths = self.sigma_file_list
        else:
            logger.warning("No defined list of sigma rules files based on recent repo cloning. Resorting to user provided list of sigma rules files.")
            if file_paths == []:
                logger.error("No list of sigma rules files provided. Exiting.")
                return

        # Create schema
        self.conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS SigmaRule(
                title STRING,
                id STRING,
                status STRING,
                description STRING,
                references STRING[],
                author STRING,
                date STRING,
                modified STRING,
                tags STRING[],
                logsource STRING[],
                detection STRING[],
                falsepositives STRING[],
                level STRING,
                PRIMARY KEY (id)
            )
        """)

        for file_path in file_paths:

            try:
                with open(file_path) as f:
                    sigma_rule_data = yaml.safe_load(f)

                logger.info(f"Loading Sigma rule: {sigma_rule_data['title']}")

                # Process the 'detection' field dynamically, storing results in a list of strings
                detection_data = []
                for selection_key, selection_value in sigma_rule_data['detection'].items():
                    if selection_key.startswith('selection_'):
                        if isinstance(selection_value, list):
                            # Handle the case where selection_value is a list
                            for item in selection_value:
                                if isinstance(item, dict):
                                    # If item is a dictionary, process it as before
                                    for field, value in item.items():
                                        if isinstance(value, list):
                                            detection_data.append(f"{selection_key}_{field}: {', '.join(value)}")
                                        else:
                                            detection_data.append(f"{selection_key}_{field}: {value}")
                                else:
                                    # If item is not a dictionary, handle it appropriately (e.g., append as is)
                                    detection_data.append(f"{selection_key}: {item}")
                        else:
                            # Handle the case where selection_value is a dictionary (as before)
                            for field, value in selection_value.items():
                                if isinstance(value, list):
                                    detection_data.append(f"{selection_key}_{field}: {', '.join(value)}")
                                else:
                                    detection_data.append(f"{selection_key}_{field}: {value}")
                    else:
                        detection_data.append(f"{selection_key}: {selection_value}")

                # Process the 'logsource' attribute
                logsource_data = [f"{key}: {value}" for key, value in sigma_rule_data['logsource'].items()]

                # Update the sigma_rule_data with the processed logsource data
                sigma_rule_data['logsource'] = logsource_data
                # Update the sigma_rule_data with the processed detection data
                sigma_rule_data['detection'] = detection_data

                self.conn.execute(f"""
                    CREATE (s:SigmaRule {{
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
                        level: {json.dumps(sigma_rule_data.get('level', 'NA'))}
                    }})
                """)
            except Exception as e:
                logger.error(f"Error loading Sigma rule: {e}. Continuing to next rule.")
                continue

        if load_to_chroma:

            try:
                self.load_sigma_to_chromadb(embedder=chroma_embedder, sigma_folder_path=self.sigma_dest_directory)
            except Exception as e:
                logger.error(f"Error loading Sigma rules to ChromaDB: {e}. Continuing to next rule.")

    def load_sigma_to_chromadb(self, embedder: str = "chroma", sigma_folder_path: str = "data/sigma", rule_quantity: int = 300) -> None:
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
        loader = DirectoryLoader(sigma_folder_path, glob="**/*.yml", use_multithreading=False, recursive=True, show_progress=True, sample_size=rule_quantity, exclude=["**/.github/**", "**/deprecated/**", "*deprecated*", "**/other/**", "*test*", "**/unsupported/**"])
        docs = loader.load()
        logger.info("Finished loading Sigma rules Document Objects")

        for doc in docs:
            file_path = Path(doc.metadata['source'])
            try:
                # Let's append necessary metadata for each document
                # Chromadb "medatadas" field is a dictionary that doesn't accept nested lists, so we need to convert the list of tags to a string of comma separated values
                with open(file_path) as f:
                    sigma_rule_data = yaml.safe_load(f)
                    logger.debug(f"Fixing Metadata for Document: {sigma_rule_data.get('title', 'NA')}")
                    doc.metadata['id'] = sigma_rule_data.get('id', str(uuid.uuid4()))
                    doc.metadata['title'] = sigma_rule_data.get('title', 'NA')
                    doc.metadata['tags'] = ', '.join(sigma_rule_data.get('tags', ['NA']))

            except Exception as e:
                logger.error(f"Error editing Document: {e}. Continuing to next rule.")
                continue

        chroma_conn = ChromaOps(embedder=EmbedderType[embedder.upper()], collection_name="sigma")
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

        query = query.lower()
        results = self.conn.execute(cypher_query)

        return results
