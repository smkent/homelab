import subprocess
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .app import CLIError
from .util import run

yaml = YAML()
yaml.preserve_quotes = True


@dataclass
class PG:
    service_name: str = "db"
    compose_file: Path = field(default_factory=lambda: Path("compose.yaml"))
    dry_run: bool = False

    @cached_property
    def compose_config(self) -> Any:
        ret = run(
            ["docker", "compose", "config"], stdout=subprocess.PIPE, text=True
        ).stdout
        return yaml.load(ret)["services"][self.service_name]

    @cached_property
    def yaml(self) -> Any:
        with open(self.compose_file) as f:
            return yaml.load(f)

    def write_yaml(self) -> Any:
        if self.dry_run:
            return
        with open(self.compose_file, "w") as f:
            return yaml.dump(self.yaml, f)
        del self.yaml

    @property
    def yaml_svc(self) -> Any:
        return self.yaml["services"][self.service_name]

    @cached_property
    def version(self) -> int:
        return int(self.compose_config["image"].split(":", 1)[1])

    @cached_property
    def environment(self) -> dict[str, str]:
        env_data = self.compose_config["environment"]
        if isinstance(env_data, list):
            dict(i.split("=", 1) for i in env_data)
        assert isinstance(env_data, dict)
        return env_data

    @cached_property
    def admin_user(self) -> str:
        return self.environment["POSTGRES_USER"]

    @cached_property
    def admin_database(self) -> str:
        return self.environment["POSTGRES_DB"]

    @cached_property
    def source_volume(self) -> Path:
        for volume in self.compose_config["volumes"]:
            if volume["target"].startswith("/var/lib/postgresql"):
                if not (path := Path(volume["source"])).is_dir():
                    raise CLIError(f"Source volume {path} is not a directory")
                return path
        raise CLIError("Unable to locate source volume")

    def set_version(self, version: int) -> None:
        self.yaml_svc["image"] = f"postgres:{version}"
        self.write_yaml()

    def set_volume_source(self, source: Path) -> None:
        for i, volume in enumerate(self.yaml_svc["volumes"]):
            if volume.split(":", 2)[1].startswith("/var/lib/postgresql"):
                rel = f"./{source.resolve().relative_to(Path('./').resolve())}"
                self.yaml_svc["volumes"][i] = f"{rel}:/var/lib/postgresql"
                break
        else:
            raise CLIError("Unable to locate data directory volume")
        self.write_yaml()
