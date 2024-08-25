from pathlib import Path

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

        if source_repo.endswith(".git"):
            full_url = source_repo
        elif "/" in source_repo:
            full_url = f"https://github.com/{source_repo}.git"
        else:
            msg = "Invalid source repository format. Please provide a full GitHub remote URL or a username/repo string."
            raise ValueError(msg)

        if destination_folder is None:
            # Extract repository name from source_repo
            repo_name = source_repo.split("/")[-1].split(".")[0]
            destination_folder = Path(Path.cwd() / repo_name)

        try:
            with tqdm(
                unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc="Cloning", total=100
            ) as progress_bar:
                Repo.clone_from(full_url, destination_folder, progress=CloneProgress(progress_bar))
            logger.info(f"Repository cloned successfully to {destination_folder}")
        except Exception as e:
            logger.error(f"Failed to clone repository: {e!s}")


class CloneProgress(RemoteProgress):
    def __init__(self, progress_bar):
        super().__init__()
        self.progress_bar = progress_bar

    def update(self, op_code, cur_count, max_count=None, message=""):
        if max_count is not None:
            self.progress_bar.total = max_count
        self.progress_bar.update(cur_count - self.progress_bar.n)
