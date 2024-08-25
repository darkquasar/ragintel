import io
import re

import docx
import pdfplumber
from bs4 import BeautifulSoup
from loguru import logger


class MultiParser:
    def parse_text_from_file(file_name: str, content: io.BytesIO) -> str:
        if file_name.endswith(".pdf"):
            with pdfplumber.open(content) as pdf:
                text = " ".join(page.extract_text() for page in pdf.pages)
        elif file_name.endswith(".html"):
            text = BeautifulSoup(
                content.read().decode("utf-8"), features="html.parser"
            ).get_text()
        elif file_name.endswith(".txt"):
            text = content.read().decode("utf-8")
        elif file_name.endswith(".docx"):
            text = " ".join(
                paragraph.text for paragraph in docx.Document(content).paragraphs
            )

        cleaned_text = re.sub(r"\s+", " ", text).strip()
        return cleaned_text
