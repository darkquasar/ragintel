import kuzu
from loguru import logger


class KuzuOps:
    def __init__(self):
        # Create an empty on-disk database and connect to it
        db = kuzu.Database("./data/ragintel.db")
