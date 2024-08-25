import os
import sys

from loguru import logger


class DirectoryManager:
    def __init__(self, log_level="INFO"):
        """Initialize the DirectoryManager with a custom log level if desired.

        Args:
            log_level (str, optional): The desired log level. Defaults to "INFO".
        """
        logger.add(sys.stderr, level=log_level)

    def create_directory(self, directory_path):
        """Creates a new directory at the specified path.

        Args:
            directory_path (str): The path of the directory to create.

        Raises:
            FileExistsError: If the directory already exists.
            OSError: If an error occurs while creating the directory.
        """

        full_path = os.path.abspath(directory_path)  # Get full path with abspath
        try:
            os.makedirs(directory_path)
            logger.info(f"Directory '{full_path}' created successfully.")
        except FileExistsError:
            logger.warning(f"Directory '{full_path}' already exists.")
        except OSError as error:
            logger.error(f"Error creating directory '{full_path}': {error}")

    def rename_directory(self, old_path, new_path):
        """Renames an existing directory.

        Args:
            old_path (str): The existing path of the directory.
            new_path (str): The new path to rename the directory to.

        Raises:
            FileNotFoundError: If the directory to rename doesn't exist.
            OSError: If an error occurs while renaming the directory.
        """

        full_path_old = os.path.abspath(old_path)  # Get full path with abspath
        full_path_new = os.path.abspath(new_path)  # Get full path with abspath

        try:
            os.rename(old_path, new_path)
            logger.info(f"Directory renamed from '{full_path_old}' to '{full_path_new}'.")
        except FileNotFoundError:
            logger.error(f"Directory '{full_path_old}' not found.")
        except OSError as error:
            logger.error(f"Error renaming directory: {error}")

    def delete_directory(self, directory_path: list[str]):
        """
        Deletes an existing directory and its contents.
        Args:
            directory_path (List[str]): The path(s) of the directory to be deleted.
        Raises:
            FileNotFoundError: If the directory is not found.
            OSError: If there is an error deleting the directory.
        Returns:
            None
        """

        if not isinstance(directory_path, list):
            directory_path = [directory_path]

        for path in directory_path:
            full_path = os.path.abspath(path)  # Get full path with abspath
            try:
                import shutil
                shutil.rmtree(full_path)
                logger.info(f"Directory '{full_path}' deleted successfully.")
            except FileNotFoundError:
                logger.error(f"Directory '{full_path}' not found.")
            except OSError as error:
                logger.error(f"Error deleting directory: {error}")
