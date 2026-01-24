import os
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import chdir, contextmanager
from functools import cached_property
from pathlib import Path

from ruamel.yaml import YAML

from .app import CLIError

HOMELAB_ENV = "HOMELAB"


class ComposeStack:
    @cached_property
    def stack_dir(self) -> Path:
        def _is_stack_dir(path: Path) -> bool:
            return path.is_dir() and all(
                (path / d).is_dir() for d in ("apps", "hosts")
            )

        if homelab_value := os.environ.get(HOMELAB_ENV):
            if _is_stack_dir(path := (Path(homelab_value) / "compose")):
                return path
            raise CLIError(
                f"{homelab_value} (via {HOMELAB_ENV}) does not exist"
            )
        git_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        if _is_stack_dir(path := git_root / "compose"):
            return path
        if _is_stack_dir(path := (Path.home() / "homelab" / "compose")):
            return path
        raise CLIError("Unable to locate stack directory")

    @cached_property
    def active_host_dir(self) -> Path:
        if not (active_dir := self.stack_dir / "hosts" / "active").is_dir():
            raise CLIError(f"{active_dir} does not exist")
        return active_dir

    @cached_property
    def host_apps_config(self) -> Path:
        if not (fn := self.active_host_dir / "apps.yml").is_file():
            raise CLIError(f"{fn} does not exist")
        return fn

    @cached_property
    def host_apps(self) -> Mapping[str, Path]:
        with self.host_apps_config.open("r", encoding="utf-8") as f:
            data = YAML().load(f)
            app_dirs = {}
            for app_name in sorted(data.get("apps", [])):
                app_dir = self.stack_dir / "apps" / app_name
                if not app_dir.exists():
                    raise CLIError(f"{app_dir} does not exist")
                app_dirs[app_name] = app_dir
        return app_dirs

    @cached_property
    def host_app_dirs(self) -> Iterator[Path]:
        for app_name in sorted(self.host_apps):
            app_dir = self.host_apps[app_name]
            with chdir(app_dir):
                yield app_dir

    def each_host_app_dir(
        self, apps: Sequence[str] | None = None
    ) -> Iterator[Path]:
        if not apps:
            yield from self.host_app_dirs
            return
        missing_apps = {
            app for app in apps if not (self.stack_dir / "apps" / app).is_dir()
        }
        if missing_apps:
            raise CLIError(
                f"App(s) do not exist: {', '.join(sorted(missing_apps))}"
            )
        for app, app_dir in [
            (app, self.stack_dir / "apps" / app) for app in sorted(apps)
        ]:
            if app not in self.host_apps:
                print(
                    f"Warning: {app} is not in"
                    f" {self.active_host_dir / 'apps.yml'}",
                    file=sys.stderr,
                )
            with chdir(app_dir):
                yield app_dir

    @contextmanager
    def app(self, app_name: str) -> Iterator[Path]:
        if app_name not in self.host_apps:
            raise CLIError(f"{app_name} is not configured on this host")
        app_dir = self.host_apps[app_name]
        with chdir(app_dir):
            yield app_dir
