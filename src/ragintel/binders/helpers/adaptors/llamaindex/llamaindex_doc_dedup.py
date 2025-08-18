import hashlib

from llama_index.core import Document
from loguru import logger


class LlamaIndexDocDedup:
    def __init__(self):
        logger.debug("Initialized LlamaIndexDocDedup")
        # Crear un objeto hash SHA-256
        self.hash = hashlib.sha256()

    def deduplicate_documents(self, documents: list[Document]) -> list[dict]:
        seen_paths = {}
        deduplicated_docs = []

        for doc in documents:
            relative_path = doc.metadata.get("relative_path")
            if relative_path not in seen_paths:
                seen_paths[relative_path] = True

                self.hash.update(str(doc.metadata.get("relative_path")).encode("utf-8"))
                doc_hash_hex = self.hash.hexdigest()

                deduplicated_docs.append(
                    {"relative_path": doc.metadata.get("relative_path"), "doc_hash": doc_hash_hex}
                )

        # logger.info(f"Deduplicated {len(documents) - len(deduplicated_docs)} documents")

        return deduplicated_docs
