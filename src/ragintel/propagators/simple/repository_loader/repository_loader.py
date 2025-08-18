from pathlib import Path

from loguru import logger

from ragintel.binders.loaders.config import ConfigLoader


class RepositoryLoader:
    """
    A class for managing and executing graph propagation tasks.
    """

    def __init__(self, config_path: str | None | Path = None):
        """
        Initializes the GraphPropagator with a configuration file.

        Args:
            config_path (str): The path to the YAML configuration file.
        """

        config_path = (
            Path(__file__).parent.parent / "ragintel" / "config" / "detection_repo_sources.yaml"
        )

        self.conf = ConfigLoader(str(config_path))
        self.conf_dict = self.conf.load_repo_config()

    def propagate(
        self,
        clone_repo: bool = True,
        load_to_graph: bool = True,
        load_to_chroma: bool = True,
        chroma_embedder: str = "ollama",
        sample_only: bool = False,
    ):
        """
        Executes the graph propagation for all sources defined in the config.

        Args:
            clone_repo (bool): Whether to clone the repository. Defaults to True.
            load_to_graph (bool): Whether to load the data to the graph. Defaults to True.
            load_to_chroma (bool): Whether to load the data to Chroma. Defaults to True.
            chroma_embedder (str): The name of the Chroma embedder to use. Defaults to "ollama".
            sample_only (bool): Whether to only load a sample of the data. Defaults to False.
        """

        try:
            for source in self.conf_dict.repos:
                loader = source.loader(source_config=source)
                docs = loader.load_nodes(
                    clone_repo=clone_repo,
                    load_to_graph=load_to_graph,
                    load_to_chroma=load_to_chroma,
                    chroma_embedder=chroma_embedder,
                    sample_only=sample_only,
                )

                return docs
        except Exception as e:
            logger.error(f"Error during graph propagation: {e}")
            return None
