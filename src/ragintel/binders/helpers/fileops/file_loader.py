import fnmatch
import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path, PosixPath, WindowsPath

from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    ObsidianLoader,
    TextLoader,
)
from loguru import logger


class FileLoader:
    def __init__(self, loader_type: str | None = None):
        self.loader_type = loader_type
        self.documents = []
        logger.debug("Initialized FileLoader loader")

    def load_single_document(self, file_name: str) -> Sequence[Document]:
        try:
            loader = TextLoader(file_name)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading file: {e}")

        return self.documents

    def load_directory(self, directory: str, glob_pattern: str) -> Sequence[Document]:
        try:
            loader = DirectoryLoader(directory, glob_pattern)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading directory: {e}")

        return self.documents

    def load_obsidian_vault(self, directory: str) -> Sequence[Document]:
        try:
            loader = ObsidianLoader(directory)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading directory: {e}")

        return self.documents

    def get_file_hash(self, file_path, algorithm="md5"):
        """
        Calculates the hash of a file using the specified algorithm.

        Args:
            filename: The path to the file.
            algorithm: The hashing algorithm to use (default: 'md5').

        Returns:
            The hexadecimal digest of the file hash.
        """

        path = Path(file_path)

        if not path.is_file():
            logger.error(f"File not found: {file_path}")
            return None

        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:  # Open in binary mode for reading
            while chunk := f.read(8192):  # Read in chunks to handle large files efficiently
                h.update(chunk)

        return h.hexdigest()

    def get_file_name(self, file_path: str) -> str:
        """Returns the file name from a given path.

        Args:
            file_path (str): The file path.

        Returns:
            str: The file name.

        Raises:
            ValueError: If the provided path is a directory.
        """
        path = Path(file_path)
        if path.is_dir():
            raise ValueError("The provided path is a directory, not a file.")
        if path.is_file():
            return path.name
        # Assume it's just the file name
        return path.name

    def list_directory_recursive(
        self,
        directory: str | Path,
        glob_patterns: Sequence[str],
        excluded_folders: Sequence[str] | None = None,
        excluded_files: Sequence[str] | None = None,
        sample_only: bool = False,
    ) -> Sequence[Path]:
        """
        Recursively lists all files matching a glob pattern within a directory, excluding files and directories
        matching any of the exclude patterns.

        Args:
            directory (str or Path): The root directory to search for files.
            glob_pattern (str): The glob pattern to match filenames against (e.g., "*.txt", "**/*.pdf").
            exclude_patterns (List[str], optional): A list of glob patterns to exclude files and directories from the search.

        Returns:
            List[Path]: A list containing the Path objects of all files matching the glob pattern
                        within the specified directory and its subdirectories.
        """
        if excluded_folders is None:
            excluded_folders = []

        if excluded_files is None:
            excluded_files = []

        if isinstance(glob_patterns, str):
            glob_patterns = [glob_patterns]

        # Check if the strings provided are actual glob patterns
        for pattern in glob_patterns:
            try:
                fnmatch.translate(pattern)
            except Exception:
                logger.warning(
                    f"You are providing an invalid glob pattern for the files to include in our recursive search. You may not get the results you are lookig for. Pattern: {pattern}"
                )

        if sample_only:
            logger.debug("Sampling 10 files for testing purposes")
            counter = 0

        directory = Path(directory)  # Ensure directory is a Path object
        all_files = []
        already_reported_exclude_folders = set()

        for glob_pattern in glob_patterns:
            logger.debug(f"Searching for files matching pattern: {glob_pattern}")
            # Loop 1: Check for excluded folders
            for path in directory.rglob(glob_pattern):
                # The comprehension bellow checks if any of the folder parts of the path contain any of the exclude patterns
                # We only check against the folder parts, not the file parts, because we want to exclude entire folders (e.g., path.parts[:-1])
                if any(pattern in part for part in path.parts[:-1] for pattern in excluded_folders):
                    if path.is_file():
                        if path.parent not in already_reported_exclude_folders:
                            already_reported_exclude_folders.add(path.parent)
                            logger.debug(f"Excluding folder: {path.parent}")
                    else:
                        if path not in already_reported_exclude_folders:
                            already_reported_exclude_folders.add(path)
                            logger.debug(f"Excluding folder: {path}")

                    continue  # Skip to the next path if it's an excluded folder

                # Loop 2: Check for excluded files (only if the path is a file and not already excluded)
                if path.is_file() and all(
                    pattern not in part for part in path.parts for pattern in excluded_files
                ):
                    logger.debug(f"Adding file: {path}")
                    all_files.append(path)
                    if sample_only:
                        counter += 1
                        if counter == 10:
                            break

        all_files = list(set(all_files))  # Remove duplicates
        logger.info(f"Found {len(all_files)} files matching the glob pattern(s)")
        return all_files

    def find_exclusion_folders(self, excluded_folders, root_folder_path, return_glob_pattern=False):
        """
        Takes a list of strings and a folder path, then identifies folders whose relative paths
        contain any of the strings, and returns a list of these exclusion folders.

        Args:
            excluded_folders: A list of strings to match against folder paths.
            root_folder_path: The path to the folder to search recursively from.

        Returns:
            A list of Path objects representing the excluded folders.
        """

        if not excluded_folders or not root_folder_path:
            logger.error("No excluded folders or root folder path provided")
            raise ValueError("No excluded folders or root folder path provided")

        exclusion_folders = []
        folder_path = Path(root_folder_path)

        for file_path in folder_path.rglob("*"):  # Iterate over all files recursively
            if file_path.is_dir():  # Consider only directories
                relative_path = file_path.relative_to(folder_path)
                if any(part in relative_path.parts for part in excluded_folders):
                    logger.debug(f"Adding folder {file_path} to exclusion list")
                    if return_glob_pattern:
                        # Convert Path object to string and add "**/*" to match anything within the folder
                        if isinstance(file_path, PosixPath):
                            glob_pattern_a = f"**/{file_path}/**/*"
                            glob_pattern_b = f"**/{file_path}/*"
                            globs = [glob_pattern_a, glob_pattern_b]
                        elif isinstance(file_path, WindowsPath):
                            glob_pattern_a = f"**{file_path}/**/*".replace("/", "\\")
                            glob_pattern_b = f"**{file_path}/*".replace("/", "\\")
                            globs = [glob_pattern_a, glob_pattern_b]
                        else:
                            raise ValueError("Unsupported path type")  # Should never happen
                        exclusion_folders.extend(globs)
                    else:
                        exclusion_folders.append(file_path)

        return exclusion_folders

    def load_and_escape_raw_file_content_for_graph_db(self, file_path: str) -> str:
        """
        Loads the content of a file and escapes any special characters.

        Args:
            file_path: The path to the file.

        Returns:
            The escaped content of the file.
        """

        with open(file_path) as f:
            doc_content = f.read()

        raw_document = json.dumps(
            re.sub(r"[\n\r]", lambda match: "\\\\" + match.group(0), doc_content)
        )

        return raw_document
