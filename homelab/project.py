import subprocess
from functools import cached_property
from pathlib import Path

from .app import CLIError


class HomelabProject:
    @cached_property
    def dir(self) -> Path:
        def _is_project_dir(path: Path) -> bool:
            return path.is_dir() and all(
                (path / d).is_dir()
                for d in (
                    "ansible/inventories",
                    "ansible/playbooks",
                    "ansible/roles",
                    "compose/apps",
                    "compose/hosts",
                    "homelab",
                )
            )

        git_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        if _is_project_dir(git_root):
            return git_root
        if _is_project_dir(path := (Path.home() / "homelab")):
            return path
        raise CLIError("Unable to locate homelab project directory")

    @cached_property
    def ansible_dir(self) -> Path:
        return self.dir / "ansible"

    @cached_property
    def stack_dir(self) -> Path:
        return self.dir / "compose"
