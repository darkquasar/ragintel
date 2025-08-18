from box import Box
from llama_index.core import Document
from loguru import logger

from ragintel.nodes.detections.gen_file_node import GenFileNode
from ragintel.propagators.base.base_propagator import BaseNodeLoader


class GenericFileLoader(BaseNodeLoader):
    def __init__(self, source_config: Box) -> None:
        super().__init__(source_config)

    def load_nodes(
        self,
        file_paths: list[str] | None = None,
        clone_repo: bool = True,
        load_to_graph: bool = True,
        load_to_vector: bool = True,
        embedder: str = "chroma",
        sample_only: bool = False,
    ) -> list[Document] | None:
        if clone_repo:
            self._clone_repo()
        else:
            logger.info("Skipped repository cloning")

        file_list = self._get_file_list(file_paths, sample_only)

        if not file_list:
            logger.error("No list of files provided. Exiting.")
            raise ValueError("No list of files provided. Exiting.")

        documents = self._load_documents_from_file_list_with_llamaindex(file_list, sample_only)

        logger.info(f"Loaded {len(documents)} documents from {len(file_list)} files")

        if load_to_graph:
            try:
                self.load_nodes_to_graphdb_llamaindex(documents=documents, node_schema=GenFileNode)
            except Exception as e:
                logger.error(f"Error loading files to KuzuDB: {e}")

        if load_to_vector:
            try:
                self.load_nodes_to_vectordb_llamaindex(documents=documents, embedder=embedder)
            except Exception as e:
                logger.error(f"Error loading files to ChromaDB: {e}")

            return None

        return documents
