"""Console script for ragintel."""

import fire
from loguru import logger


def help() -> None:
    print("ragintel")
    print("=" * len("ragintel"))
    print("Test")


def main() -> None:
    fire.Fire({"help": help})


if __name__ == "__main__":
    main()  # pragma: no cover
