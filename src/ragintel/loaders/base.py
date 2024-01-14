class Loader:
    def __init__(self, loader_type: str, output_type: str = "") -> None:
        self.loader_type: str = loader_type
        self.output_type: str = output_type

        if self.loader_type == "":
            self.loader_type = "simple_html"
