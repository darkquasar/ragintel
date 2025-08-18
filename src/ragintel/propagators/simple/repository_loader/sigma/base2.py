# Description: This file contains the SigmaLoader class, which is responsible for loading Sigma rules into the database.
from collections.abc import Sequence
from pathlib import Path
from typing import no_type_check

import yaml
from box import Box
from llama_index.core import Document
from loguru import logger
from pydantic._internal._model_construction import ModelMetaclass

from ragintel.binders.helpers.adaptors.pydantic import PydanticAdaptor
from ragintel.nodes.detections import SigmaNode2
from ragintel.propagators.base.base_propagator import BaseNodeLoader


class SigmaLoader2(BaseNodeLoader):
    def __init__(self, source_config: Box) -> None:
        super().__init__(source_config)

    @no_type_check
    def load_nodes(
        self,
        file_paths: list[str] | None = None,
        clone_repo: bool = True,
        load_to_graph: bool = True,
        load_to_vector: bool = True,
        embedder: str = "chroma",
        sample_only: bool = False,
    ) -> Sequence[Document] | None:
        if clone_repo:
            self._clone_repo()
        else:
            logger.info("Skipped repository cloning")

        file_list = self._get_file_list(file_paths, sample_only)

        if not file_list:
            logger.error("No list of files provided. Exiting.")
            raise ValueError("No list of files provided. Exiting.")

        documents = self.load_documents_from_file_list_with_langchain(
            sample_only=sample_only, convert_to_llamaindex_document=True
        )

        for document in documents:
            self.expand_sigma_document_metadata(document)

        logger.info(f"Loaded {len(documents)} documents")

        if load_to_graph:
            try:
                self.load_nodes_to_graphdb_llamaindex(documents=documents, node_schema=SigmaNode2)
            except Exception as e:
                logger.error(f"Error loading files to KuzuDB: {e}")

        if load_to_vector:
            try:
                self.load_nodes_to_vectordb_llamaindex(documents=documents, embedder=embedder)
            except Exception as e:
                logger.error(f"Error loading files to ChromaDB: {e}")

            return None

        return documents

    def expand_sigma_document_metadata(self, document: Document) -> Document:
        # This function will allow us to expand the metadata of a Sigma rule document

        file_path = Path(document.metadata["source"])

        try:
            with open(file_path) as f:
                sigma_rule_data = yaml.safe_load(f)

                logger.debug(f"Processing Document: {document.metadata.get('file_name', 'NA')}")

                document.metadata["title"] = sigma_rule_data.get("title", "NA")
                document.metadata["tags"] = ", ".join(sigma_rule_data.get("tags", ["NA"]))
                document.metadata["sigma_id"] = sigma_rule_data.get("id", "NA")
                document.metadata["status"] = sigma_rule_data.get("status", "NA")
                document.metadata["description"] = sigma_rule_data.get("description", "NA")
                document.metadata["references"] = sigma_rule_data.get("references", "NA")
                document.metadata["author"] = sigma_rule_data.get("author", "NA")
                document.metadata["date"] = sigma_rule_data.get("date", "NA")
                document.metadata["modified"] = sigma_rule_data.get("modified", "NA")
                document.metadata["logsource"] = sigma_rule_data.get("logsource", ["NA"])
                document.metadata["detection"] = sigma_rule_data.get("detection", ["NA"])
                document.metadata["falsepositives"] = sigma_rule_data.get("falsepositives", "NA")
                document.metadata["level"] = sigma_rule_data.get("level", "NA")

                logger.debug(
                    f"Expanded Metadata for Document: {document.metadata.get('title', 'NA')}"
                )

        except Exception as e:
            logger.error(f"Error editing Document: {e}. Continuing to next rule.")

        return document

    def parse_sigma_detection_data(self, sigma_rule_detection_data: dict) -> list[str]:  # type: ignore
        # Process the 'detection' field dynamically, storing results in a list of strings
        detection_data = []

        for selection_key, selection_value in sigma_rule_detection_data.items():
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

        return detection_data

    def parse_sigma_logsource_data(self, sigma_rule_logsource_data: dict) -> list[str]:  # type: ignore
        # Process the 'logsource' attribute
        logsource_data = [f"{key}: {value}" for key, value in sigma_rule_logsource_data.items()]

        return logsource_data

    def load_nodes_to_graph(
        self,
        documents: Sequence[Document],
        node_schema: ModelMetaclass,
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

        # We cast the document metadata to the Pydantic schema
        # The Pydantic schema has a Validator that will ensure the data is parsed correctly
        # We need to pass in the current instance of the BaseNodeLoader to the Pydantic schema as "self"
        for doc in documents:
            data = node_schema(doc.metadata, self)
            print(data.model_dump_json())

        logger.info("Finished loading Sigma rules to KuzuDB")
