from typing import List

import html2text
from langchain.docstore.document import Document
from loguru import logger


class ConvertHTMLToText:
    def __init__(self, docs: List[Document], parser: str = "langchain.html_parser"):

        self.parser = parser
        self.docs = docs
        self.clean_html_docs = []

    def convert_html_to_text(self) -> List[Document]:

        """
        Convert HTML content to plain text using html2text either directly or via langchain
        """

        if self.parser == "ragintel.html2text":

            logger.info("Converting HTML to plain text using ragintel.html2text")
            for doc in self.docs:
                raw_html = doc.page_content
                clean_html_text = html2text.html2text(raw_html)
                html_document = Document(
                    page_content=clean_html_text,
                    metadata={"source": "ragintel.html2text"},
                )
                self.clean_html_docs.append(html_document)

        if self.parser == "langchain.html_parser":

            logger.info("Converting HTML to plain text using langchain.html_parser")

            try:
                from langchain.document_transformers import Html2TextTransformer
            except ImportError:
                logger.error("Missing langchain's Html2TextTransformer library")

            # Transform
            _html2text = Html2TextTransformer()
            docs_transformed = _html2text.transform_documents(self.docs)

            self.clean_html_docs = docs_transformed

        logger.info(
            f"Converted {len(self.clean_html_docs)} HTML documents to plain text"
        )
