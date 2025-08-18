from loguru import logger
from pydantic import BaseModel, model_validator

from ragintel.binders.helpers.adaptors.decorators import as_ragintel_node


@as_ragintel_node
class GenFileNode(BaseModel):
    node_type: str = "detection"
    node_subtype: str = "GenFileNode"
    source_url: str
    id: str
    file_name: str
    file_hash: str
    raw_document: str

    @model_validator(mode="before")
    @classmethod
    def extract_data(cls, data):
        """
        Extracts data using methods from the provided loader.
        """
        loader = data.get("loader")  # Access the loader instance
        if loader:
            data["source_url"] = loader.get_llamaindex_doc_metadata("doc_url", data)
            data["id"] = loader.get_llamaindex_doc_metadata("file_name", data)
            data["file_name"] = loader.get_llamaindex_doc_metadata("file_name", data)
            data["file_hash"] = loader.get_llamaindex_doc_metadata("file_hash", data)
            data["raw_document"] = loader.load_and_escape_raw_file_content_for_graph_db(
                data.get("relative_path")
            )
        return data
