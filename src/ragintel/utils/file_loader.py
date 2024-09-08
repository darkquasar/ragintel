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

    def load_directory(self, directory: str, glob_pattern: str) -> list[Document]:
        try:
            loader = DirectoryLoader(directory, glob_pattern)
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
        self,
        directory: str | Path,
        glob_patterns: list[str],
        exclude_patterns: list[str] | None = None,
        sample_only: bool = False,
    ) -> list[Path]:
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
        if exclude_patterns is None:
            exclude_patterns = []

        if sample_only:
            logger.debug("Sampling 5 files for testing purposes")
            counter = 0

        directory = Path(directory)  # Ensure directory is a Path object
        all_files = []

        for glob_pattern in glob_patterns:
            _glob_pattern = f"**/*{glob_pattern}"  # Convert to a proper n-depth glob
            for path in directory.rglob(_glob_pattern):
                if path.is_file() and not any(path.match(pattern) for pattern in exclude_patterns):
                    all_files.append(path)
                    if sample_only:
                        counter += 1
                        if counter == 5:
                            break

        all_files = list(set(all_files))  # Remove duplicates
        logger.info(f"Found {len(all_files)} files matching the glob pattern(s)")
        return all_files
