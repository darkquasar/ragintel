import importlib

import yaml
from box import Box
from loguru import logger


class ConfigLoader:
    """Loads YAML configuration files."""

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file

    def load_repo_config(self, config_file: str | None = None) -> Box:
        """Parses a YAML configuration file.

        Args:
            config_file (str): The path to the YAML configuration file.

        Returns:
            dict: The parsed configuration data.

        Raises:
            FileNotFoundError: If the configuration file is not found.
            ValueError: If the configuration file is not valid YAML.
        """

        if self.config_file is not None:
            config_file = self.config_file

        try:
            with open(config_file) as file:
                self.config_yaml = yaml.safe_load(file)
                self.config = Box(self.config_yaml)
                logger.info(f"Loaded configuration file: {config_file}")

            # Filter out the repo items where 'skip' is True, and log the skipped URLs
            filtered_repos = []
            for repo in self.config.repos:
                if repo.skip:
                    logger.info(f"Skipping source: {repo.repo_url}")
                else:
                    filtered_repos.append(repo)

            self.config.repos = filtered_repos

            for source in self.config.repos:
                # Pass a pointer to the Loader class instance to the configuration
                module_path, class_name = source.loader.rsplit(".", 1)
                module = importlib.import_module(module_path)
                loader_class_ = getattr(module, class_name)
                source.loader = loader_class_

                # Pass a pointer to the Node Schema class instance to the configuration
                module_path, class_name = source.node_schema.rsplit(".", 1)
                module = importlib.import_module(module_path)
                node_class_ = getattr(module, class_name)
                source.node_schema = node_class_

            return self.config

        except FileNotFoundError:
            msg = f"Configuration file not found: {config_file}"
            raise FileNotFoundError(msg) from None
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML configuration: {exc}"
            raise ValueError(msg) from exc
