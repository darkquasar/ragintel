import uuid
from datetime import date

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from ragintel.binders.helpers.adaptors.decorators import as_ragintel_node


@as_ragintel_node
class SigmaNode2(BaseModel):
    node_type: str = "detection"
    node_subtype: str = "sigma"
    source_url: str
    title: str
    id: str
    sigma_id: str
    file_name: str
    file_hash: str
    status: str
    description: str
    references: list[str] | str = Field(
        ..., json_schema_extra={"graphdb_field_type": f"{list[str]}"}
    )
    author: str
    date: date | str
    modified: str
    tags: list[str] | str
    logsource: list[str] | str
    detection: list[str] | str
    falsepositives: list[str] | str
    level: str
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
            data["id"] = str(uuid.uuid4())
            data["file_name"] = loader.get_llamaindex_doc_metadata("file_name", data)
            data["file_hash"] = loader.get_llamaindex_doc_metadata("file_hash", data)
            data["raw_document"] = loader.load_and_escape_raw_file_content_for_graph_db(
                data.get("source")
            )

            # Assuming your loader has methods to extract these fields
            data["title"] = loader.get_llamaindex_doc_metadata("title", data)
            data["sigma_id"] = loader.get_llamaindex_doc_metadata("id", data)
            data["status"] = loader.get_llamaindex_doc_metadata("status", data)
            data["description"] = loader._escape_string(
                loader.get_llamaindex_doc_metadata("description", data)
            )
            data["references"] = loader.get_llamaindex_doc_metadata("references", data)
            data["author"] = loader._escape_string(
                loader.get_llamaindex_doc_metadata("author", data)
            )
            data["date"] = loader._escape_string(
                loader._convert_date_to_string(loader.get_llamaindex_doc_metadata("date", data))
            )
            data["modified"] = loader._escape_string(
                loader._convert_date_to_string(loader.get_llamaindex_doc_metadata("modified", data))
            )
            data["tags"] = loader.get_llamaindex_doc_metadata("tags", data)
            data["logsource"] = loader._escape_list_and_return_string(
                loader.parse_sigma_logsource_data(
                    loader.get_llamaindex_doc_metadata("logsource", data)
                )
            )
            data["detection"] = loader._escape_list_and_return_string(
                loader.parse_sigma_detection_data(
                    loader.get_llamaindex_doc_metadata("detection", data)
                )
            )
            data["falsepositives"] = loader.get_llamaindex_doc_metadata("falsepositives", data)
            data["level"] = loader._escape_string(loader.get_llamaindex_doc_metadata("level", data))
            data["raw_document"] = loader.load_and_escape_raw_file_content_for_graph_db(
                data.get("source")
            )

        return data
