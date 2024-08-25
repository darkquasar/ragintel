from pathlib import Path

from loguru import logger


class DirectoryManager:
    def __init__(self, log_level="INFO"):
        """Initialize the DirectoryManager with a custom log level if desired.

        Args:
            log_level (str, optional): The desired log level. Defaults to "INFO".
        """

    def create_directory(self, directory_path):
        """Creates a new directory at the specified path.

        Args:
            directory_path (str or Path): The path of the directory to create.

        Raises:
            FileExistsError: If the directory already exists.
            OSError: If an error occurs while creating the directory.
        """

        full_path = Path(directory_path).resolve()  # Convert to Path and resolve
        try:
            full_path.mkdir(parents=True, exist_ok=False)  # Create directory, raise error if exists
            logger.info(f"Directory '{full_path}' created successfully.")
        except FileExistsError:
            logger.warning(f"Directory '{full_path}' already exists.")
        except OSError as error:
            logger.error(f"Error creating directory '{full_path}': {error}")

    def rename_directory(self, old_path, new_path):
        """Renames an existing directory.

        Args:
            old_path (str or Path): The existing path of the directory.
            new_path (str or Path): The new path to rename the directory to.

        Raises:
            FileNotFoundError: If the directory to rename doesn't exist.
            OSError: If an error occurs while renaming the directory.
        """

        full_path_old = Path(old_path).resolve()
        full_path_new = Path(new_path).resolve()

        try:
            full_path_old.rename(full_path_new)
            logger.info(f"Directory renamed from '{full_path_old}' to '{full_path_new}'.")
        except FileNotFoundError:
            logger.error(f"Directory '{full_path_old}' not found.")
        except OSError as error:
            logger.error(f"Error renaming directory: {error}")

    def delete_directory(self, directory_paths: list[str], whatif: bool = True):
        """
        Deletes directories and their contents, but only if they are within the "data" folder
        in the user's home directory or the package root folder.

        Args:
            directory_paths (List[str] or List[Path]): The path(s) of the directories to be deleted.
            whatif (bool, optional): If True, simulates the deletion and returns the directories that would be deleted
                                    without actually deleting them. Defaults to False.

        Raises:
            FileNotFoundError: If any of the directories are not found.
            OSError: If there is an error deleting any of the directories (only when `whatif` is False).
            PermissionError: If attempting to delete a directory outside the allowed "data" folders.

        Returns:
            None (if `whatif` is False)
            List[Path]: A list of Path objects representing the directories that would be deleted (if `whatif` is True).
        """

        # Check if directory_paths is a string and convert it to a list if needed
        if isinstance(directory_paths, str):
            directory_paths = [directory_paths]

        allowed_data_dirs = [
            Path.home() / "data",
            Path(__file__).parent.resolve().parent / "data",
            Path(__file__).resolve().parent.parent.parent.parent / "jupyter/data",
        ]

        directories_to_delete = []  # Store directories that would be deleted

        for path in directory_paths:
            full_path = Path(path).resolve()

            # Check if the path is within one of the allowed data directories
            if not any(allowed_dir in full_path.parents for allowed_dir in allowed_data_dirs):
                msg = f"Cannot delete '{full_path}'. It's outside the allowed 'data' folders."
                raise PermissionError(msg)

            try:
                if not full_path.exists():
                    raise FileNotFoundError  # Raise error even in whatif mode

                if whatif:
                    directories_to_delete.append(full_path)
                    logger.info(f"[WHATIF] Would delete directory '{full_path}'.")
                else:
                    import shutil

                    shutil.rmtree(full_path)
                    logger.info(f"Directory '{full_path}' deleted successfully.")
            except FileNotFoundError:
                logger.error(f"Directory '{full_path}' not found.")
            except OSError as error:
                if not whatif:  # Only raise OSError if not in whatif mode
                    logger.error(f"Error deleting directory: {error}")
