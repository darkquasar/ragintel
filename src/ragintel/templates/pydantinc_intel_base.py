
from loguru import logger
from pydantic import BaseModel, Field


class RagIntelMITRE(BaseModel):

    """RAG Intel MITRE model"""

    article_name: str = Field(description="Full title of the article")
    mitre_ttps: list[str] = Field(
        description="MITRE ATT&CK subtechniques that best apply to the article"
    )
    short_description: str = Field(
        description="Summary of the article that captures the main issue and provides context around main techqniques used by the threat actor"
    )
