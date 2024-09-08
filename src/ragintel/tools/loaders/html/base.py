import uuid

import html2text
from langchain.docstore.document import Document
from loguru import logger


class HTMLLoader:
    def __init__(self):
        self.clean_html_docs = []
        self.documents = []

    def convert_html_to_text(
        self, docs: list[Document], parser: str = "langchain.html_parser"
    ) -> list[Document]:
        """
        Convert HTML content to plain text using html2text either directly or via langchain
        """
        self.docs = docs

        if parser == "ragintel.html2text":
            logger.info("Converting HTML to plain text using ragintel.html2text")
            for doc in self.docs:
                raw_html = doc.page_content
                clean_html_text = html2text.html2text(raw_html)
                html_document = Document(
                    page_content=clean_html_text,
                    metadata={"parser": "ragintel.html2text", "id": str(uuid.uuid4())},
                )
                self.clean_html_docs.append(html_document)

        if parser == "langchain.html_parser":
            logger.info("Converting HTML to plain text using langchain.html_parser")

            try:
                from langchain_community.document_transformers import Html2TextTransformer
            except ImportError:
                logger.error("Missing langchain's Html2TextTransformer library")

            # Transform
            _html2text = Html2TextTransformer()
            docs_transformed = _html2text.transform_documents(self.docs)

            for doc in docs_transformed:
                doc.metadata = {"parser": "langchain.html_parser", "id": str(uuid.uuid4())}

            self.clean_html_docs = docs_transformed

        logger.info(f"Converted {len(self.clean_html_docs)} HTML documents to plain text")

        return self.clean_html_docs

    def load_html(
        self, url: list | str = ..., loader_type: str = "ragintel.simple_html"
    ) -> list[Document]:
        """
        Load HTML content from the specified URL and convert it to plain text.
        """
        self.url = url
        self.loader_type = loader_type
        self.docs = []

        if type(self.url) is str:
            self.url = [self.url]

        if self.loader_type == "ragintel.simple_html":
            try:
                import requests
            except ImportError:
                logger.error("Missing requests library")

            # Use requests to fetch the HTML content
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
            }

            for url in self.url:
                response = requests.get(url, headers=headers)
                html_documents = Document(
                    page_content=response.text,
                    metadata={"source": "ragintel.simple_html"},
                )
                self.documents.append(html_documents)

        elif self.loader_type == "langchain.async_html":
            try:
                from langchain_community.document_loaders import AsyncChromiumLoader
            except ImportError:
                logger.error("Missing langchain AsyncChromiumLoader library")

            try:
                loader = AsyncChromiumLoader(self.url)
                html_documents = loader.load()
                self.documents = html_documents
            except Exception as e:
                logger.error(f"Error loading HTML content with AsyncChromiumLoader: {e}")

        elif self.loader_type == "langchain.web_based_loader":
            try:
                from langchain_community.document_loaders import WebBaseLoader
            except ImportError:
                logger.error("Missing langchain WebBaseLoader library")

            # Logic still to be implemented
            loader = WebBaseLoader(self.url)
            html_documents = loader.load()
            self.documents = html_documents

        else:
            logger.error("Missing loader type")

        logger.info(f"Loaded {len(self.documents)} HTML documents")
        return self.documents

    def load_html_with_filter(self, html_tag_filters: list) -> str:
        """
        Load HTML content, apply a custom filter function, and convert it to plain text.
        """
        return "todo"
