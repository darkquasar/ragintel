from collections.abc import Sequence

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import LangchainNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode
from loguru import logger


class LangChainDocumentSplitter:
    # We implement a default chunk size of 1024 and a default overlap of 20
    # as per https://www.llamaindex.ai/blog/evaluating-the-ideal-chunk-size-for-a-rag-system-using-llamaindex-6207e5d3fec5
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document_by_recursive_char(self, docs: Sequence[Document]) -> Sequence[Document]:
        """
        Split text into sentences using langchain's RecursiveCharacterTextSplitter
        """

        # Transform
        self.docs = docs
        self.document_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        self.nodes = self.document_splitter.transform_documents(self.docs)

        logger.info(f"Split {len(self.docs)} documents into {len(self.nodes)} chunks")

        return self.nodes


class LlamaIndexDocumentSplitter:
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document_by_recursive_char(self, docs: Sequence[LlamaDocument]) -> list[BaseNode]:
        """
        Split text into sentences using langchain's RecursiveCharacterTextSplitter wrapped in LlamaIndex LangchainNodeParser
        """

        # Transform
        self.docs = docs
        self.document_splitter = LangchainNodeParser(
            RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
        )
        self.nodes = self.document_splitter.get_nodes_from_documents(self.docs)

        logger.info(f"Split {len(self.docs)} documents into {len(self.nodes)} chunks")

        return self.nodes

    def split_document_by_sentence(self, docs: Sequence[LlamaDocument]) -> list[BaseNode]:
        """
        Split text into sentences using langchain's SentenceSplitter
        """

        # Transform
        self.docs = docs
        self.document_splitter = SentenceSplitter()
        self.nodes = self.document_splitter.get_nodes_from_documents(self.docs)

        logger.info(f"Split {len(self.docs)} documents into {len(self.nodes)} chunks")

        return self.nodes
