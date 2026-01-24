import sys
from abc import abstractmethod


class CLIError(Exception):
    pass


class HomelabCLIApp:
    @classmethod
    def app(cls) -> None:
        try:
            cls().main()
        except CLIError as e:
            print(f"Error: {e}", file=sys.stderr)

    @abstractmethod
    def main(self) -> None:
        pass
