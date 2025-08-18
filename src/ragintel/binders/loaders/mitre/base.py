from langchain.docstore.document import Document
from loguru import logger


class MitreLoader:
    def __init__(self):
        self.clean_html_docs = []
        self.docs = []
        # TBD

    def load_mitre_attack(self, url: str = "https://attack.mitre.org/"):
        """
        Load MITRE ATT&CK content from the specified URL and convert it to plain text.
        """
        self.url = url

        if self.url == "https://attack.mitre.org/":
            logger.info("Loading MITRE ATT&CK content from attack.mitre.org")
            self.docs = []
            self.docs.append(
                Document(page_content="MITRE ATT&CK content", metadata={"source": "MITRE ATT&CK"})
            )
            self.clean_html_docs = self.convert_html_to_text(self.docs, parser="ragintel.html2text")

        return self.clean_html_docs
