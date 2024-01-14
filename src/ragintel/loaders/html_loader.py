from typing import Optional, Type

import html2text

from ..loaders.base import Loader


class HtmlLoader:
    def __init__(self, loader: Type[Loader], url: list):

        self.loader = loader
        self.url = url
        self.raw_html_content = ""

    def load_clear_html(self) -> str:
        """
        Load HTML content from the specified URL and convert it to plain text.
        """

        for url in self.url:

            if self.loader.loader_type == "simple_html":

                try:
                    import requests
                except ImportError:
                    print("Missing library")

                # Use requests to fetch the HTML content
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
                }
                response = requests.get(url, headers=headers)
                html_content = response.text

                # Use html2text to convert HTML to clean ASCII text
                self.raw_html_content = html_content

            elif self.loader.loader_type == "langchain_async_html":

                try:
                    from langchain.document_loaders import AsyncChromiumLoader
                except ImportError:
                    print("cannot load library")

                # Logic still to be implemented
                langc_loader = AsyncChromiumLoader([url])
                html_content = langc_loader.load()
                self.raw_html_content = html_content

            yield self.raw_html_content

    def load_html_with_filter(self, html_tag_filters: list) -> str:
        """
        Load HTML content, apply a custom filter function, and convert it to plain text.
        """
        todo = "todo"
        return todo
