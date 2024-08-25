"""Top-level package for ragintel."""
from loguru import logger

__author__ = """Diego Perez"""
__email__ = "darkquasar7@gmail.com"
__version__ = "0.1.0"

import os

from dotenv import load_dotenv

from ragintel.templates.enums import EmbedderType

# Get the absolute path to the package's root directory
package_root = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file (relative to package root)
load_dotenv(os.path.join(package_root, '.env'))
