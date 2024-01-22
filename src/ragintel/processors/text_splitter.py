from typing import List

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger


class TextSplitter:
    def __init__(
        self, docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 100
    ):

        self.docs = docs
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text_recursive_char(self) -> List[Document]:

        """
        Split text into sentences using langchain's RecursiveCharacterTextSplitter
        """

        # Transform
        recursive_splitter = RecursiveCharacterTextSplitter()
        self.split_docs = recursive_splitter.transform_documents(self.docs)

        logger.info(
            f"Split {len(self.docs)} documents into {len(self.split_docs)} sub-documents (sentences)"
        )

        return self.split_docs
