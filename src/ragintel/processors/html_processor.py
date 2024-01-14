from typing import Optional, Type

import html2text
from langchain.docstore.document import Document


class ConvertHTMLToText:
    def __init__(self, doc: Document, parser: str = "html2text"):

        self.parser = parser
        self.doc = doc

    def convert_html_to_text(self, raw_html: str):

        """
        Convert HTML content to plain text using html2text either directly or via langchain
        """

        self.clean_html_text = ""

        if self.parser == "html2text":

            clean_html_text = html2text.html2text(raw_html)
            self.clean_html_text = clean_html_text

        if self.parser == "langchain_html_parser":

            try:
                from langchain.document_transformers import Html2TextTransformer
            except ImportError:
                print("cannot load library")

            if self.doc is None:
                # Construct Document instance to ensure parsing
                doc = Document(page_content=raw_html, metadata={"source": "local"})

            # Transform
            _html2text = Html2TextTransformer()
            docs_transformed = _html2text.transform_documents([doc])

            self.clean_html_text = docs_transformed
