import random
import string

import yaml
from box import Box
from langchain.vectorstores import OpenSearchVectorSearch
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from opensearchpy import OpenSearch

from ragintel.utils import config_loader


class OpenSearchDB:
    def __init__(
        self,
        url: list[str] | None = None,
        config_file: str | None = None,
        username: str = "admin",
        password: str = "admin",
    ):
        if config_file is not None:
            _config_loader = config_loader.ConfigLoader()
            config = _config_loader.load_config(config_file)

            self.OPENSEARCH_URL = config.vectordb.config.opensearch_url
            self.OPENSEARCH_USERNAME = config.vectordb.config.http_auth.user
            self.OPENSEARCH_PASSWORD = config.vectordb.config.http_auth.passw

            logger.debug(f"OpenSearch URL: {self.OPENSEARCH_URL}")

        else:
            self.OPENSEARCH_URL = url
            self.OPENSEARCH_USERNAME = username
            self.OPENSEARCH_PASSWORD = password

        self.client = OpenSearch(
            hosts=self.OPENSEARCH_URL,
            http_auth=(self.OPENSEARCH_USERNAME, self.OPENSEARCH_PASSWORD),
            use_ssl=False,
            verify_certs=False,
            http_compress=True,
        )

        logger.info(f"Connected to OpenSearch at {self.OPENSEARCH_URL}")

    def create_index(self, index_name: str, body: dict | None = None):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        if body is None:
            logger.warning("No index body provided, using default settings")
            index_body = {
                "settings": {"index.knn": True},
                "mappings": {
                    "properties": {
                        "vector_field": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "engine": "faiss",
                                "name": "hnsw",
                                "space_type": "l2",
                            },
                        }
                    }
                },
            }
        else:
            index_body = body

        logger.debug(yaml.dump(index_body, indent=4))

        self.client.indices.create(index=index_name, body=index_body)
        logger.info(f"Created OpenSearch index {index_name}")

    def update_index_properties(self, index_name: str, body: dict):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        if body is None:
            logger.error("No index body provided for updating index properties")
            msg = "No index body provided"
            raise ValueError(msg)

        self.client.indices.put_settings(index=index_name, body=body)
        logger.info(f"Updated OpenSearch index {index_name} properties")

    def delete_index(self, index_name: str):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        self.client.indices.delete(index=index_name)
        logger.info(f"Deleted OpenSearch index {index_name}")

    def generate_random_id(length=10):
        alphanumeric = string.ascii_letters + string.digits
        return "".join(random.choice(alphanumeric) for _ in range(length))

    def add_document(self, index_name: str, document: dict, document_id: str | None = None):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        if document is None:
            logger.error("No document provided")
            msg = "No document provided"
            raise ValueError(msg)

        if document_id is None:
            document_id = self.generate_random_id(10)

        self.client.index(index=index_name, id=document_id, body=document)
        logger.info(f"Indexed document with ID {document_id} into OpenSearch index {index_name}")

    def search_document(self, index_name: str, query: dict, size: int = 10):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        if query is None:
            logger.error("No query provided. Please provide a query in the form of a dictionary")
            msg = "No query provided"
            raise ValueError(msg)

        if size is None:
            logger.warning("No size provided, using default size")
            size = 10

        results = self.client.search(index=index_name, body=query, size=size)
        logger.info(f"Search results: {results}")
        return results

    def update_document(self, index_name: str, document: dict, document_id: str | None = None):
        if index_name is None:
            logger.error("No index name provided")
            msg = "No index name provided"
            raise ValueError(msg)

        if document is None:
            logger.error("No document provided")
            msg = "No document provided"
            raise ValueError(msg)

        if document_id is None:
            logger.warning("No document ID provided, using default ID")
            document_id = "1"

        self.client.update(index=index_name, id=document_id, body=document)
        logger.info(f"Updated document with ID {document_id} in OpenSearch index {index_name}")


class OpensearchLanchainClient:
    def __init__(
        self,
        index: str | None = None,
        config_dict: dict | None = None,
        url: list[str] | None = None,
        config_file: str | None = None,
        username: str = "admin",
        password: str = "admin",
    ):
        if config_dict is not None:
            config = Box(config_dict)

        elif config_file is not None:
            _config_loader = config_loader.ConfigLoader()
            config = _config_loader.load_config(config_file)

        else:
            self.OPENSEARCH_URL = url
            self.OPENSEARCH_USERNAME = username
            self.OPENSEARCH_PASSWORD = password

        if config is not None:
            self.OPENSEARCH_URL = config.vectordb.config.opensearch_url
            self.OPENSEARCH_USERNAME = config.vectordb.config.http_auth.user
            self.OPENSEARCH_PASSWORD = config.vectordb.config.http_auth.passw
            self.OPENAI_API_KEY = config.llm.config.api_key

            logger.debug(f"Langchain Client OpenSearch URL: {self.OPENSEARCH_URL}")

        self.embeddings = OpenAIEmbeddings(openai_api_key=self.OPENAI_API_KEY)
        logger.debug("Initialized OpenAIEmbeddings")

        self.vector_store = OpenSearchVectorSearch(
            opensearch_url=self.OPENSEARCH_URL,
            http_auth=(self.OPENSEARCH_USERNAME, self.OPENSEARCH_PASSWORD),
            index_name=index,
            embedding_function=self.embeddings,
            http_compress=True,  # enables gzip compression for request bodies
            verify_certs=False,
        )

    def add_documents(self, index: str, documents: list[dict]):
        self.vector_store = OpenSearchVectorSearch(
            opensearch_url=self.OPENSEARCH_URL,
            http_auth=(self.OPENSEARCH_USERNAME, self.OPENSEARCH_PASSWORD),
            index_name=index,
            embedding_function=self.embeddings,
            http_compress=True,  # enables gzip compression for request bodies
            verify_certs=False,
        )

        self.vector_store.add_documents(documents, bulk_size=1500)

    def show_vector_store(self):
        pass
