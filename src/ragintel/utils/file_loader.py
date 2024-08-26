import glob
import os
from pathlib import Path

from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    ObsidianLoader,
    UnstructuredFileLoader,
)
from loguru import logger


class FileLoader:
    def __init__(self, loader_type: str | None = None):
        self.loader_type = loader_type
        self.documents = []
        logger.debug("Initialized FileLoader loader")

    def load_single_document(self, file_name: str) -> list[Document]:
        try:
            loader = UnstructuredFileLoader(file_name)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading file: {e}")

        return self.documents

    def load_directory(self, directory: str, glob: str) -> list[Document]:
        try:
            loader = DirectoryLoader(directory, glob)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading directory: {e}")

        return self.documents

    def load_obsidian_vault(self, directory: str) -> list[Document]:
        try:
            loader = ObsidianLoader(directory)
            self.documents = loader.load()
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading directory: {e}")

        return self.documents

    def list_directory_recursive(
        self, directory: str, glob_pattern: str, exclude_patterns: list[str] | None = None
    ) -> list[str]:
        """Recursively lists all files matching a glob pattern within a directory.

        :param directory: str, the root directory to search for files.
        :param glob_pattern: str, the glob pattern to match filenames against (e.g., "*.txt", "**/*.pdf").
        :param exclude_patterns: List[str], a list of glob patterns to exclude files and directories from the search.

        Example:
        {
            "directory": "/path/to/my/directory",
            "glob_pattern": "*.txt",
            "exclude_patterns": ["*.tmp", "temp/"]
        }

        Returns:
        - List[str], a list containing the full paths of all files matching the glob pattern within the specified directory and its subdirectories.
        """
        if exclude_patterns is None:
            exclude_patterns = []

        all_files = []

        for root, dirs, files in os.walk(directory):
            # Exclude directories based on patterns
            dirs[:] = [
                d
                for d in dirs
                if not any(glob.fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns)
            ]

            for file in files:
                if glob.fnmatch.fnmatch(file, glob_pattern) and not any(
                    glob.fnmatch.fnmatch(file, pattern) for pattern in exclude_patterns
                ):
                    full_path = Path(root / file)
                    all_files.append(full_path)

        return all_files
