from datetime import date
from typing import Union, get_args, get_origin

from loguru import logger


class PydanticAdaptor:
    def pydantic_to_schema_string(self, model_class, parse_and_return=False):
        """
        Converts a Pydantic model class into a string literal schema representation.

        Args:
            model_class: The Pydantic model class to convert.
            parse_and_return: If True, returns only the type string for single field parsing.

        Returns:
            A string representing the schema, suitable for placing within triple quotes in KuzuDB.
        """
        schema_lines = []

        for field_name, field_info in model_class.model_fields.items():
            # Handle aliases if present
            _field_name = field_info.alias if field_info.alias else field_name

            # Get the KuzuDB type for this field
            type_str = self._get_kuzu_type(field_name, field_info, parse_and_return)

            if parse_and_return:
                return type_str

            schema_lines.append(f"  {_field_name} {type_str},")

        # Add the PRIMARY KEY line if 'id' is present
        if "id" in model_class.model_fields:
            schema_lines.append("  PRIMARY KEY (id)")

        return "\n".join(schema_lines)

    def _get_kuzu_type(self, field_name: str, field_info, parse_and_return: bool = False) -> str:
        """
        Determines the appropriate KuzuDB type for a Pydantic field.

        Args:
            field_name: Name of the field
            field_info: Pydantic field info object
            parse_and_return: If True, this is a recursive call for type parsing

        Returns:
            KuzuDB type string
        """
        annotation = field_info.annotation

        # First check if there's a custom graphdb_field_type override
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            graphdb_field_type = field_info.json_schema_extra.get("graphdb_field_type")
            if graphdb_field_type:
                # logger.debug(f"Field {field_name} using custom graphdb_field_type: {graphdb_field_type}")
                return "STRING[]"  # Most custom types are string arrays

        # Handle Union types
        origin = get_origin(annotation)
        if origin is Union:
            return self._handle_union_type(field_name, annotation)

        # Handle List types
        if origin is list or annotation == list[str]:
            return "STRING[]"

        # Handle simple types
        return self._handle_simple_type(field_name, annotation)

    def _handle_union_type(self, field_name: str, annotation) -> str:
        """
        Handles Union type annotations by selecting the most appropriate type for KuzuDB.

        Args:
            field_name: Name of the field
            annotation: The Union type annotation

        Returns:
            KuzuDB type string
        """
        args = get_args(annotation)
        # logger.debug(f"Field {field_name} is Union type with args: {args}")

        # Common Union patterns and their KuzuDB mappings
        if len(args) == 2:
            # Union[List[str], str] -> STRING[] (prefer array type)
            has_list_str = any(
                arg == list[str] or (get_origin(arg) is list and get_args(arg) == (str,))
                for arg in args
            )
            if has_list_str and str in args:
                # logger.debug(f"Field {field_name} Union[List[str], str] -> STRING[]")
                return "STRING[]"

            # Union[date, str] -> STRING (prefer string for flexibility)
            if date in args and str in args:
                # logger.debug(f"Field {field_name} Union[date, str] -> STRING")
                return "STRING"

            # Union[int, str] -> STRING
            if int in args and str in args:
                # logger.debug(f"Field {field_name} Union[int, str] -> STRING")
                return "STRING"

        # Default fallback: use the first non-None type, or STRING if all else fails
        for arg in args:
            if arg is not type(None):  # Skip NoneType
                kuzu_type = self._handle_simple_type(field_name, arg)
                if kuzu_type != "STRING":  # If we got a specific type, use it
                    # logger.debug(f"Field {field_name} Union fallback to: {kuzu_type}")
                    return kuzu_type

        # logger.debug(f"Field {field_name} Union fallback to STRING")
        return "STRING"

    def _handle_simple_type(self, field_name: str, annotation) -> str:
        """
        Maps simple Python types to KuzuDB types.

        Args:
            field_name: Name of the field
            annotation: The type annotation

        Returns:
            KuzuDB type string
        """
        # Direct type mappings
        type_mapping = {
            str: "STRING",
            int: "INT64",
            float: "DOUBLE",
            bool: "BOOLEAN",
            date: "DATE",
        }

        # Check direct mapping first
        if annotation in type_mapping:
            kuzu_type = type_mapping[annotation]
            # logger.debug(f"Field {field_name} mapped {annotation} -> {kuzu_type}")
            return kuzu_type

        # Handle List types that weren't caught earlier
        origin = get_origin(annotation)
        if origin is list:
            args = get_args(annotation)
            if args and args[0] is str:
                # logger.debug(f"Field {field_name} List[str] -> STRING[]")
                return "STRING[]"

        # Fallback for unknown types
        logger.warning(
            f"Field {field_name} has unsupported type: {annotation}, defaulting to STRING"
        )
        return "STRING"
