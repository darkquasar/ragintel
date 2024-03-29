import yaml
from box import Box
from loguru import logger


class ConfigLoader:
    """Loads YAML configuration files."""

    def __init__(self, config_file: str = None):
        self.config_file = config_file

    def load_config(self, config_file: str) -> Box:
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
            with open(config_file, "r") as file:
                self.config_yaml = yaml.safe_load(file)
                self.config = Box(self.config_yaml)
                logger.info(f"Loaded configuration file: {config_file}")
                return self.config

        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML configuration: {exc}")
