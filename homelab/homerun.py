import argparse
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import chdir
from functools import cached_property, partial
from pathlib import Path

import yaml

from .util import run


class Homedo:
    def main(self) -> None:
        for i, app_dir in enumerate(self.host_app_dirs):
            if i:
                print()
            print(f">>> {app_dir}")
            run(["docker", "compose"] + list(self.extra_args))

    @cached_property
    def stack_dir(self) -> Path:
        git_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        if not (
            git_root.is_dir()
            and (stack_dir := git_root / "compose").is_dir()
            and (stack_dir / "apps").is_dir()
            and (stack_dir / "hosts").is_dir()
        ):
            raise Exception("Unable to locate stack directory")
        return stack_dir

    @cached_property
    def active_host_dir(self) -> Path:
        if not (active_dir := self.stack_dir / "hosts" / "active").is_dir():
            raise Exception(f"{active_dir} does not exist")
        return active_dir

    @cached_property
    def host_apps_config(self) -> Path:
        if not (fn := self.active_host_dir / "apps.yml").is_file():
            raise Exception(f"{fn} does not exist")
        return fn

    @cached_property
    def host_app_dirs(self) -> Iterator[Path]:
        with self.host_apps_config.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            app_dirs = set()
            for app_name in sorted(data.get("apps", [])):
                app_dir = Path(self.stack_dir / "apps" / app_name)
                if not app_dir.exists():
                    raise Exception(f"{app_dir} does not exist")
                app_dirs.add(app_dir)
            for app_dir in sorted(app_dirs):
                with chdir(app_dir):
                    yield app_dir

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
        return ap.parse_known_args()


main = partial(Homedo().main)
