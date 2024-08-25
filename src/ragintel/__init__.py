"""Top-level package for ragintel."""

from loguru import logger

__author__ = """Diego Perez"""
__email__ = "darkquasar7@gmail.com"
__version__ = "0.1.0"


from pathlib import Path

from dotenv import load_dotenv

# Get the absolute path to the package's root directory
package_root = Path(__file__).resolve().parent

# Load environment variables from .env file (relative to package root)
load_dotenv(Path(package_root) / ".env")
