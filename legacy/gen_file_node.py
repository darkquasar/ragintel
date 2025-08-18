from loguru import logger
from pydantic import BaseModel


class GenFileNode(BaseModel):
    node_type: str = "detection"
    node_subtype: str = "GenFileNode"
    source_url: str
    title: str
    id: str
    file_hash: str
    raw_document: str

    class Config:
        populate_by_name = True
