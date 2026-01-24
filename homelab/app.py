import sys
from abc import ABC

from typer import Typer


class CLIError(Exception):
    pass


class HomelabCLIApp(ABC):
    cli: Typer

    @classmethod
    def app(cls) -> None:
        try:
            cls.cli()
        except CLIError as e:
            print(f"Error: {e}", file=sys.stderr)
