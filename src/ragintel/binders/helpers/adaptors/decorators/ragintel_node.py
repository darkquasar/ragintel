from functools import wraps

from loguru import logger

from ragintel.propagators.base.base_propagator import BaseNodeLoader


def as_ragintel_node(model_class):
    """
    Decorator to add a custom __init__ to a Pydantic model.
    """
    original_init = model_class.__init__  # Store original __init__

    @wraps(original_init)  # Preserve original __init__ metadata
    def custom_init(self, raw_data: dict, loader: BaseNodeLoader, **data):
        """
        Custom __init__ to use the provided loader.
        """
        raw_data["loader"] = loader
        original_init(self, **raw_data, **data)  # Call the original __init__

    model_class.__init__ = custom_init  # Replace __init__ with the custom one

    return model_class
