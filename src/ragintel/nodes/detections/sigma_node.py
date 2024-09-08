from loguru import logger
from pydantic import BaseModel


class SigmaNode(BaseModel):
    node_type: str = "detection"
    node_subtype: str = "sigma"
    source_url: str
    title: str
    id: str
    status: str
    description: str
    references: list[str]
    author: str
    date: str
    modified: str
    tags: list[str]
    logsource: list[str]
    detection: list[str]
    falsepositives: list[str]
    level: str
    raw_document: str

    class Config:
        populate_by_name = True
