import sys
import textwrap
from collections.abc import Sequence
from contextlib import chdir
from dataclasses import dataclass, field
from functools import cached_property
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any, Literal

from typer import Argument, BadParameter, Context, Option, Typer

from .app import HomelabCLIApp
from .project import HomelabProject
from .util import gpg_fifo, run


class HomestarOptions:
    class Validators:
        @classmethod
        def string(cls, value: str) -> str:
            if not value:
                raise BadParameter("Value cannot be empty")
            return value

        @classmethod
        def file_path(cls, value: str) -> Path:
            path = Path(cls.string(value))
            if not path.exists():
                raise BadParameter(f"{path} does not exist")
            return path

        @classmethod
        def playbook_path(cls, value: str) -> Path:
            fn = cls.string(str(value))
            if not fn.endswith(".yml"):
                fn += ".yml"
            path = Path(fn)
            with chdir("playbooks"):
                if not path.exists():
                    raise BadParameter(f"{path} does not exist")
            return path

    playbook = Annotated[
        Path,
        Option(  # ty: ignore[no-matching-overload]
            "-p",
            "--playbook",
            metavar="playbook",
            callback=Validators.playbook_path,
            default_factory="main",
            help="Ansible playbook",
        ),
    ]
    env = Annotated[
        str,
        Option(  # ty: ignore[no-matching-overload]
            "-e",
            "--env",
            metavar="env",
            callback=Validators.string,
            default_factory="live",
            help="Ansible inventory",
        ),
    ]
    ansible_vault = Annotated[
        Path,
        Option(  # ty: ignore[no-matching-overload]
            "-V",
            "--vault",
            metavar="path",
            callback=Validators.file_path,
            default_factory=Path("vault/ansible.asc"),
            help="Path to Ansible vault",
        ),
    ]


@dataclass
class Homestar(HomelabCLIApp):
    dry_run: bool = False
    invoke_cwd: Path = field(default_factory=Path.cwd)

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

    @cached_property
    def mitogen_path(self) -> str:
        spec = find_spec("ansible_mitogen")
        assert spec and spec.origin, "ansible_mitogen module not found"  # noqa: S101, PT018
        return str(Path(spec.origin).parent / "plugins" / "strategy")

    def ansible_run(
        self,
        cmd: Sequence[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        kwargs.setdefault("env", {})
        kwargs["env"] |= {
            "ANSIBLE_STRATEGY_PLUGINS": self.mitogen_path,
        }
        return run(cmd, *args, dry_run=self.dry_run, **kwargs)

    @cli.callback()
    @staticmethod
    def setup(
        ctx: Context,
        *,
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
        *,
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
            cmd = ["sudo", "-E", "rsync", "-avHSP", "--delete"]
            if ctx.obj.dry_run:
                cmd += ["-n"]
            if action == "get":
                if not ctx.obj.dry_run:
                    Path(local_path).mkdir(parents=True)
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
        *,
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
            print(cmd)  # noqa: T201
            ctx.obj.ansible_run(cmd)

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
        *,
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
            print(hostvars_playbook)  # noqa: T201
            ctx.obj.ansible_run(cmd, input=hostvars_playbook, text=True)

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
        *,
        playbook: HomestarOptions.playbook,
        env: HomestarOptions.env,
        ansible_vault: HomestarOptions.ansible_vault,
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
            ctx.obj.ansible_run(cmd)
