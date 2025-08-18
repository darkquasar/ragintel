import os

import kuzu
from loguru import logger
from pandas import DataFrame


class KuzuOps:
    def __init__(self, db_path: str | None = None):
        if not db_path:
            db_path = os.getenv("KUZU_DB_PERSIST_DIRECTORY", "./data/raginteldb")

        db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(db)

        logger.debug(f"Initialized KuzuOps with DB {db_path}")

    def query_graph(self, cypher_query: str, output_type: str = "DataFrame") -> DataFrame:
        cypher_query = cypher_query.lower()
        cypher_query_results = self.conn.execute(cypher_query)
        cypher_query_results_df = cypher_query_results.get_as_df()

        return cypher_query_results_df

    def get_detection_id_by_file_name(self, file_name: str) -> list | None:
        """Checks if a detection node with the given file_name exists in KuzuDB.

        Args:
            file_name: The name of the file.

        Returns:
            The document ID if a match is found, None otherwise.
        """

        cypher_query = f"""
            MATCH (d:detections {{file_name: '{file_name}'}})
            RETURN d.id AS id
        """

        df = self.query_graph(cypher_query)

        if not df.empty:
            ids = []
            for index in range(len(df)):  # Iterate over all rows
                id = df.iloc[index].to_dict()["id"]
                ids.append(id)

            return ids

        return None

    def get_node_id_by_file_name_and_hash(self, file_name: str, file_hash: str) -> list | None:
        """Checks if a node with the given file_name and file_hash exists in KuzuDB.

        Args:
            file_name: The name of the file.
            file_hash: The hash of the file.

        Returns:
            The document ID if a match is found, None otherwise.
        """
        cypher_query = f"""
            MATCH (d {{file_name: '{file_name}', file_hash: '{file_hash}'}})
            RETURN d.id AS id
        """

        df = self.query_graph(cypher_query)

        if not df.empty:
            ids = []
            for index in range(len(df)):  # Iterate over all rows
                id = df.iloc[index].to_dict()["id"]
                ids.append(id)

            return ids

        return None

    def delete_node_by_id(self, node_ids: str | list) -> list | None:
        """Checks if a node with the given file_name and file_hash exists in KuzuDB.

        Args:
            file_name: The name of the file.
            file_hash: The hash of the file.

        Returns:
            The document ID if a match is found, None otherwise.
        """

        cypher_query = f"""
            MATCH (d)
            WHERE d.id IN {node_ids!s}
            DELETE d
            RETURN d.id AS id
        """

        if isinstance(node_ids, str):
            node_ids = [node_ids]

        if not node_ids:
            logger.error("No node IDs provided")
            raise ValueError("No node IDs provided")

        df = self.query_graph(cypher_query)

        if not df.empty:
            ids = []
            for index in range(len(df)):  # Iterate over all rows
                id = df.iloc[index].to_dict()["id"]
                ids.append(id)

            return ids

        return None
