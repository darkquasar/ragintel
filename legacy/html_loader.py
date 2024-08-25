
from langchain.docstore.document import Document
from loguru import logger


class HtmlLoader:
    def __init__(self, loader_type: str):

        self.loader_type = loader_type
        self.documents = []

    def load_html(self, url: list | str = ...) -> list[Document]:
        """
        Load HTML content from the specified URL and convert it to plain text.
        """
        self.url = url

        if type(self.url) == str:
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
                from langchain.document_loaders import AsyncChromiumLoader
            except ImportError:
                logger.error("Missing langchain AsyncChromiumLoader library")

            loader = AsyncChromiumLoader(self.url)
            html_documents = loader.load()
            self.documents = html_documents

        elif self.loader_type == "langchain.web_based_loader":

            try:
                from langchain.document_loaders import WebBaseLoader
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
        todo = "todo"
        return todo
