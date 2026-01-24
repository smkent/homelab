import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property

from .app import HomelabCLIApp
from .stack import ComposeStack
from .util import run


@dataclass
class Homerun(HomelabCLIApp):
    stack: ComposeStack = field(default_factory=ComposeStack)

    def main(self) -> None:
        if not self.extra_args:
            return
        for i, app_dir in enumerate(
            self.stack.each_host_app_dir(self.args.apps)
        ):
            if i:
                print()
            print(f">>> {app_dir}")
            run(["docker", "compose"] + list(self.extra_args))

    @cached_property
    def args(self) -> argparse.Namespace:
        return self._args[0]

    @cached_property
    def extra_args(self) -> Sequence[str]:
        return self._args[1]

    @cached_property
    def _args(self) -> tuple[argparse.Namespace, Sequence[str]]:
        ap = argparse.ArgumentParser(
            description=(
                "Repeat `docker compose` commands for all enabled apps"
            ),
        )
        ap.add_argument(
            "-a",
            "--app",
            dest="apps",
            action="append",
            help=(
                "Run command on the specified app, instead of all enabled apps"
            ),
        )
        return ap.parse_known_args()
