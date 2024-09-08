from loguru import logger


class PydanticAdaptor:
    def pydantic_to_schema_string(self, model_class):
        """
        Converts a Pydantic model class into a string literal schema representation.

        Args:
            model_class: The Pydantic model class to convert.

        Returns:
            A string representing the schema, suitable for placing within triple quotes in KuzuDB.
        """

        schema_lines = []
        for field_name, field_info in model_class.model_fields.items():
            # Handle aliases if present
            _field_name = field_info.alias if field_info.alias else field_name

            # Determine the type representation
            if field_info.annotation is str:
                type_str = "STRING"
            elif (
                field_info.annotation.__origin__ is list
                and field_info.annotation.__args__[0] is str
            ):
                type_str = "STRING[]"
            else:
                type_str = field_info.annotation.__name__.upper()

            schema_lines.append(f"  {_field_name} {type_str},")

        # Add the PRIMARY KEY line if 'id' is present
        if "id" in model_class.model_fields:
            schema_lines.append("  PRIMARY KEY (id)")

        return "\n".join(schema_lines)
