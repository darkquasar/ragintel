from unittest.mock import MagicMock, patch

import pytest
from langchain.docstore.document import Document
from loguru import logger

from ragintel.tools.html_processor import Processor


@pytest.fixture
def processor():
    return Processor()


def test_convert_html_to_text_ragintel(processor):
    docs = [Document(page_content="<html><body>Test</body></html>")]
    with patch("html2text.html2text", return_value="Test"):
        result = processor.convert_html_to_text(docs, parser="ragintel.html2text")
    assert len(result) == 1
    assert result[0].page_content == "Test"
    assert result[0].metadata["parser"] == "ragintel.html2text"


def test_convert_html_to_text_langchain(processor):
    docs = [Document(page_content="<html><body>Test</body></html>")]
    mock_transformer = MagicMock()
    mock_transformer.transform_documents.return_value = [Document(page_content="Test")]
    with patch(
        "langchain_community.document_transformers.Html2TextTransformer",
        return_value=mock_transformer,
    ):
        result = processor.convert_html_to_text(docs, parser="langchain.html_parser")
    assert len(result) == 1
    assert result[0].page_content == "Test"
    assert result[0].metadata["parser"] == "langchain.html_parser"


def test_load_html_ragintel(processor):
    url = "http://example.com"
    mock_response = MagicMock()
    mock_response.text = "<html><body>Test</body></html>"
    with patch("requests.get", return_value=mock_response):
        result = processor.load_html(url, loader_type="ragintel.simple_html")
    assert len(result) == 1
    assert result[0].page_content == "<html><body>Test</body></html>"
    assert result[0].metadata["source"] == "ragintel.simple_html"


def test_load_html_langchain_async(processor):
    """
    For this unit test, we need to download playwright browsers: playwright install.
    """
    url = "http://example.com"
    mock_loader = MagicMock()
    mock_loader.load.return_value = [Document(page_content="Test")]
    with patch(
        "langchain_community.document_loaders.AsyncChromiumLoader", return_value=mock_loader
    ):
        result = processor.load_html(url, loader_type="langchain.async_html")
    assert len(result) == 1
    assert result[0].page_content == "Test"


def test_load_html_langchain_web_based(processor):
    url = "http://example.com"
    mock_loader = MagicMock()
    mock_loader.load.return_value = [Document(page_content="Test")]
    with patch("langchain_community.document_loaders.WebBaseLoader", return_value=mock_loader):
        result = processor.load_html(url, loader_type="langchain.web_based_loader")
    assert len(result) == 1
    assert result[0].page_content == "Test"
