from abc import abstractmethod


class HomelabCLIApp:
    @classmethod
    def app(cls) -> None:
        cls().main()

    @abstractmethod
    def main(self) -> None:
        pass
