from enum import Enum

from loguru import logger


class EmbedderType(Enum):
    CHROMA = "chroma"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
