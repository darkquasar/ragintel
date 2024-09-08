from pathlib import Path, PurePosixPath
from urllib.parse import quote

from git import RemoteProgress, Repo
from loguru import logger
from tqdm import tqdm

# from crewai_tools import tool


class GitHubLoader:
    def __init__(self):
        pass

    def clone_repository(self, source_repo: str, destination_folder: str | None = None) -> None:
        """Clones a GitHub repository to the specified destination folder.

        :param source_repo: str, the GitHub repository to clone. It can be a full GitHub remote URL or a username/repo string.
        :param destination_folder: str, the destination folder where the repository will be cloned. If not provided, it will be cloned to the current working directory.

        Example:
        {
            "source_repo": "https://github.com/username/repo.git",
            "destination_folder": "/path/to/destination"
        }

        Note: If the source_repo ends with ".git", it will be used as is. Otherwise, it will be appended with ".git" to form the full URL.

        Raises:
        - ValueError: If the source repository format is invalid.

        """

        if "https://github.com/" in source_repo:
            full_url = source_repo
        elif "https://github.com/" not in source_repo and len(source_repo.split("/")) == 2:
            full_url = f"https://github.com/{source_repo}"
        else:
            msg = "Invalid source repository format. Please provide a full GitHub remote URL or a username/repo string."
            raise ValueError(msg)

        if destination_folder is None:
            # Extract repository name from source_repo
            repo_name = self.find_repo_name(source_repo)
            destination_folder = Path(Path.cwd() / repo_name)

        if isinstance(destination_folder, str):
            destination_folder = Path(destination_folder)

        if destination_folder.exists():
            logger.warning(
                f"Destination folder {destination_folder} already exists. Skipping cloning."
            )
            return

        try:
            with tqdm(
                unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc="Cloning", total=100
            ) as progress_bar:
                Repo.clone_from(full_url, destination_folder, progress=CloneProgress(progress_bar))
                logger.info(f"Repository cloned successfully to {destination_folder}")
        except Exception as e:
            logger.error(f"Failed to clone repository: {e!s}")

    def find_repo_name(self, base_url: str) -> str:
        # Extract the repository name from the base URL
        repo_name = PurePosixPath(base_url).parts[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        return repo_name

    def find_repo_url(self, file_path: str, base_url: str) -> str:
        # Extract the repository name from the base URL
        repo_name = PurePosixPath(base_url).parts[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Find the index of "repo" in the path parts, this is the relative path from where the file is located
        # it doesn't matter what is the directory structure since we should know the repo name by its base url and
        # we can use that to calculate the url of any files under the directory structure of the cloned repository
        file_path_parts = Path(file_path).parts
        file_index = file_path_parts.index(repo_name)

        # Join the parts from repo name onwards
        relative_path = PurePosixPath(*file_path_parts[file_index + 1 :])
        # Join the base URL and the relative path
        full_url = f"{base_url}/blob/main/{relative_path!s}"

        logger.debug(f"File Full URL: {quote(full_url, safe=":/")}")

        return quote(full_url, safe=":/")


class CloneProgress(RemoteProgress):
    def __init__(self, progress_bar):
        super().__init__()
        self.progress_bar = progress_bar

    def update(self, op_code, cur_count, max_count=None, message=""):
        if max_count is not None:
            self.progress_bar.total = max_count
        self.progress_bar.update(cur_count - self.progress_bar.n)
