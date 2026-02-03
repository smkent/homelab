import hashlib
import os
import sys
import textwrap
from collections.abc import Sequence
from contextlib import chdir
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Literal

from typer import Argument, BadParameter, Context, Option, Typer

from .app import HomelabCLIApp
from .project import HomelabProject
from .util import gpg_fifo, run


@dataclass
class AnsibleCollections:
    project: HomelabProject = field(default_factory=HomelabProject)

    @cached_property
    def requirements(self) -> Path:
        return self.project.ansible_dir / "requirements.yml"

    @cached_property
    def checksum(self) -> Path:
        return (
            self.requirements.parent / f".{self.requirements.name}.sha256sum"
        )

    def ensure(self) -> None:
        if not self._requirements_changed():
            return
        run(
            [
                "ansible-galaxy",
                "collection",
                "install",
                "-r",
                str(self.requirements),
            ],
        )
        self._update_checksum()

    def _requirements_changed(self) -> bool:
        if not self.checksum.exists():
            return True
        new_checksum = hashlib.sha256(
            self.requirements.read_bytes()
        ).hexdigest()
        old_checksum = self.checksum.read_text().strip()
        return new_checksum != old_checksum

    def _update_checksum(self) -> None:
        self.checksum.write_text(
            hashlib.sha256(self.requirements.read_bytes()).hexdigest()
        )


class HomestarOptions:
    class Validators:
        @classmethod
        def _str(cls, value: str) -> str:
            if not value:
                raise BadParameter("Value cannot be empty")
            return value

        @classmethod
        def _file(cls, value: str) -> Path:
            path = Path(cls._str(value))
            if not path.exists():
                raise BadParameter(f"{path} does not exist")
            return path

        @classmethod
        def _playbook_path(cls, value: str) -> Path:
            fn = cls._str(str(value))
            if not fn.endswith(".yml"):
                fn += ".yml"
            path = Path(fn)
            with chdir("playbooks"):
                if not path.exists():
                    raise BadParameter(f"{path} does not exist")
            return path

    playbook = Annotated[
        Path,
        Option(
            "-p",
            "--playbook",
            metavar="playbook",
            callback=Validators._playbook_path,
            default_factory="main",
            help="Ansible playbook",
        ),
    ]
    env = Annotated[
        str,
        Option(
            "-e",
            "--env",
            metavar="env",
            callback=Validators._str,
            default_factory="live",
            help="Ansible inventory",
        ),
    ]
    ansible_vault = Annotated[
        Path,
        Option(
            "-V",
            "--vault",
            metavar="path",
            callback=Validators._file,
            default_factory=Path("vault/ansible.asc"),
            help="Path to Ansible vault",
        ),
    ]


@dataclass
class Homestar(HomelabCLIApp):
    dry_run: bool = False
    invoke_cwd: Path = Path(".").resolve()
    ansible_collections: AnsibleCollections = field(
        default_factory=AnsibleCollections
    )

    cli = Typer(
        help="Homelab setup",
        add_completion=False,
        no_args_is_help=True,
        pretty_exceptions_enable=False,
        rich_markup_mode=None,
    )

    @classmethod
    def app(cls) -> None:
        project = HomelabProject()
        with chdir(project.ansible_dir):
            return super().app()

    def _ansible_run(
        self,
        cmd: Sequence[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        self.ansible_collections.ensure()
        return run(cmd, *args, dry_run=self.dry_run, **kwargs)

    @cli.callback()
    @staticmethod
    def setup(
        ctx: Context,
        ansible_help: Annotated[
            bool,
            Option(
                "-H",
                "--ansible-help",
                help="Show ansible-playbook help message and exit",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            Option(
                "-n",
                "--dry-run",
                "--pretend",
                help="Print commands to execute",
            ),
        ] = False,
    ) -> None:
        if ansible_help:
            run(["ansible-playbook", "--help"])
            sys.exit(0)
        ctx.obj = Homestar(dry_run=dry_run)

    @cli.command(help="Get or put compose app(s) data from or onto a host")
    @staticmethod
    def appdata(
        ctx: Context,
        ansible_vault: HomestarOptions.ansible_vault,
        action: Annotated[Literal["get", "put"], Argument(help="Action")],
        host: Annotated[str, Argument(metavar="host", help="Target host")],
        apps: Annotated[
            list[str], Argument(metavar="app", help="Selected application(s)")
        ],
        local_dir: Annotated[
            Path,
            Option(
                "-d",
                "--dir",
                metavar="path",
                help="Path for local data copy",
                default_factory=lambda: Homestar.invoke_cwd / "app_data",
                show_default="./app_data",
            ),
        ],
    ) -> None:
        for app in apps:
            remote_path = (
                f"root@{host}:/opt/deploy/homelab/compose/volumes/{app}/"
            )
            local_path = (Path(local_dir) / app).as_posix()
            if not local_path.endswith("/"):
                local_path += "/"
            cmd = ["sudo", "-E", "rsync", "-avHSP"]
            if ctx.obj.dry_run:
                cmd += ["-n"]
            if action == "get":
                if not ctx.obj.dry_run:
                    os.makedirs(local_path, exist_ok=True)
                cmd += [remote_path, local_path]
            elif action == "put":
                cmd += [local_path, remote_path]
            run(cmd)

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
        help="Bootstrap new host",
    )
    @staticmethod
    def bootstrap(
        ctx: Context,
        ansible_vault: HomestarOptions.ansible_vault,
        host: Annotated[str, Argument(metavar="host", help="Target host")],
        username: Annotated[
            str, Argument(metavar="username", help="Username on target host")
        ],
        sudo: Annotated[
            bool,
            Option(
                "--sudo",
                help="User sudo instead of su for initial bootstrapping",
            ),
        ] = False,
    ) -> None:
        with gpg_fifo(ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"{host},",
                "-u",
                username,
                "--ask-pass",
                "--ask-become-pass",
                "-e",
                f"installation_user={username}",
                "-e",
                f"@{fifo}",
                "playbooks/bootstrap.yml",
            ]
            if sudo:
                cmd += ["-e", "bootstrap_become_method=sudo"]
            cmd += ctx.args
            print(cmd)
            ctx.obj._ansible_run(cmd)

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
        help="Print host variables",
    )
    @staticmethod
    def hostvars(
        ctx: Context,
        env: HomestarOptions.env,
        ansible_vault: HomestarOptions.ansible_vault,
        message: Annotated[
            str,
            Option(
                "-m",
                "--message",
                metavar="expression",
                help="Expression for Ansible `debug` module",
            ),
        ] = '"{{hostvars[inventory_hostname]}}"',
    ) -> None:
        with gpg_fifo(ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"inventories/{env}/hosts.yml",
                "-e",
                f"@{fifo}",
                "/dev/stdin",
            ]
            cmd += ctx.args
            hostvars_playbook = textwrap.dedent(
                f"""
            - hosts: all
              gather_facts: true
              tasks:
                - ansible.builtin.debug:
                    msg: {message}
            """
            )
            print(hostvars_playbook)
            ctx.obj._ansible_run(cmd, input=hostvars_playbook, text=True)

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
        help="Deploy",
    )
    @staticmethod
    def run(
        ctx: Context,
        playbook: HomestarOptions.playbook,
        env: HomestarOptions.env,
        ansible_vault: HomestarOptions.ansible_vault,
        message: Annotated[
            str,
            Option(
                "-m",
                "--message",
                metavar="expression",
                help="Expression for Ansible `debug` module",
            ),
        ] = '"{{hostvars[inventory_hostname]}}"',
    ) -> None:
        with gpg_fifo(ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"inventories/{env}/hosts.yml",
                "-e",
                f"@{fifo}",
                f"playbooks/{playbook}",
            ]
            cmd += ctx.args
            ctx.obj._ansible_run(cmd)
