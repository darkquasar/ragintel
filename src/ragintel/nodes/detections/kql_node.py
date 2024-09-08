from loguru import logger
from pydantic import BaseModel


class KQLNode(BaseModel):
    node_type: str = "detection"
    node_subtype: str = "kql"
    source_url: str
    title: str
    id: str
    raw_document: str

    class Config:
        populate_by_name = True
