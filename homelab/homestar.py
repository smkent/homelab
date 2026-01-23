import argparse
import hashlib
import os
import sys
import textwrap
from collections.abc import Sequence
from contextlib import chdir
from dataclasses import dataclass
from functools import cached_property, partial
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from .util import gpg_fifo, run


@dataclass
class AnsibleCollections:
    requirements: Path

    @cached_property
    def checksum(self) -> Path:
        return (
            self.requirements.parent / f".{self.requirements.name}.sha256sum"
        )

    @cached_property
    def collections(self) -> Path:
        return self.requirements.parent / "collections"

    @cached_property
    def env(self) -> dict[str, str]:
        return {
            "ANSIBLE_GALAXY_COLLECTIONS_PATH_WARNING": "false",
            "ANSIBLE_COLLECTIONS_PATH": str(self.collections.resolve()),
        }

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
                "-p",
                str(self.collections),
            ],
            env=os.environ | self.env,
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


class Homestar:
    def main(self) -> None:
        with as_file(files(__package__) / "ansible") as ansible_path:
            if getattr(self.args, "chdir", False):
                with chdir(ansible_path):
                    self.args.func()
            else:
                self.args.func()

    def _ansible_run(
        self,
        cmd: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        self.ansible_collections.ensure()
        return run(
            cmd,
            env=env or (os.environ | self.ansible_collections.env),
            dry_run=self.args.dry_run,
            **kwargs,
        )

    def action_bootstrap(self) -> None:
        with gpg_fifo(self.args.ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"{self.args.host},",
                "-u",
                self.args.username,
                "--ask-pass",
                "--ask-become-pass",
                "-e",
                f"installation_user={self.args.username}",
                "-e",
                f"@{fifo}",
                "playbooks/bootstrap.yml",
            ]
            cmd += self.extra_args
            self._ansible_run(cmd)

    def action_hostvars(self) -> None:
        with gpg_fifo(self.args.ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"inventories/{self.args.env}/hosts.yml",
                "-e",
                f"fqdn={self.args.fqdn}",
                "-e",
                f"@{fifo}",
                "/dev/stdin",
            ]
            cmd += self.extra_args
            playbook = textwrap.dedent(
                f"""
            - hosts: all
              gather_facts: true
              tasks:
                - ansible.builtin.debug:
                    msg: {self.args.message}
            """
            )
            print(playbook)
            self._ansible_run(cmd, input=playbook, text=True)

    def action_run(self) -> None:
        with gpg_fifo(self.args.ansible_vault) as fifo:
            cmd = [
                "ansible-playbook",
                "-i",
                f"inventories/{self.args.env}/hosts.yml",
                "-e",
                f"fqdn={self.args.fqdn}",
                "-e",
                f"@{fifo}",
                f"playbooks/{self.args.playbook}",
            ]
            cmd += self.extra_args
            self._ansible_run(cmd)

    def action_appdata(self) -> None:
        for app in self.args.apps:
            remote_path = (
                f"root@{self.args.host}:"
                f"/opt/deploy/homelab/compose/apps/{app}/data/"
            )
            local_path = (Path(self.args.local_dir) / app / "data").as_posix()
            # run(["sudo", "-E", "env"])
            if not local_path.endswith("/"):
                local_path += "/"
            cmd = ["sudo", "-E", "rsync", "-avHSP"]
            if self.args.dry_run:
                cmd += ["-n"]
            if self.args.action == "get":
                if not self.args.dry_run:
                    os.makedirs(local_path, exist_ok=True)
                cmd += [remote_path, local_path]
            elif self.args.action == "put":
                cmd += [local_path, remote_path]
            run(cmd)

    @cached_property
    def args(self) -> argparse.Namespace:
        return self._args[0]

    @cached_property
    def extra_args(self) -> Sequence[str]:
        return self._args[1]

    @cached_property
    def _args(self) -> tuple[argparse.Namespace, Sequence[str]]:
        def _str(value: str) -> str:
            if not value:
                raise argparse.ArgumentTypeError("Value cannot be empty")
            return value

        def _playbook_path(value: str) -> Path:
            fn = _str(value)
            if not fn.endswith(".yml"):
                fn += ".yml"
            path = Path(fn)
            with chdir("ansible/playbooks"):
                if not path.exists():
                    raise argparse.ArgumentTypeError(f"{path} does not exist")
            return path

        class AnsibleHelp(argparse.Action):
            def __call__(self, *args: object, **kwargs: object) -> None:
                run(["ansible-playbook", "--help"])
                sys.exit(0)

        ansible_mixin = argparse.ArgumentParser(add_help=False)
        ansible_mixin.add_argument(
            "-H",
            "--ansible-help",
            nargs=0,
            action=AnsibleHelp,
            help="show ansible-playbook help message and exit",
        )
        ansible_mixin.add_argument(
            "-p",
            "--playbook",
            metavar="playbook",
            type=_playbook_path,
            default="main",
            help="Ansible playbook (default: %(default)s)",
        )
        ansible_mixin.add_argument(
            "-e",
            "--env",
            metavar="env",
            type=_str,
            default="live",
            help="Ansible inventory (default: %(default)s)",
        )
        ansible_mixin.add_argument(
            "-f",
            "--fqdn",
            metavar="fqdn",
            type=_str,
            default="smkent.net",
            help="Domain name (default: %(default)s)",
        )

        ansible_vault_mixin = argparse.ArgumentParser(add_help=False)
        ansible_vault_mixin.add_argument(
            "-V",
            "--vault",
            dest="ansible_vault",
            metavar="path",
            type=_str,
            default="vault/ansible.asc",
            help="Path to Ansible vault (default: %(default)s)",
        )

        ap = argparse.ArgumentParser(
            description=(
                "Homelab provisioner, not to be confused with Homestar Runner"
            ),
        )
        ap.add_argument(
            "-n",
            "--dry-run",
            "--pretend",
            dest="dry_run",
            action="store_true",
            help="Print commands to execute",
        )
        subp = ap.add_subparsers(title="Subcommands", metavar="command")

        appdata_p = subp.add_parser(
            "appdata",
            parents=[ansible_vault_mixin],
            help="Get or put compose app(s) data from or onto a host",
        )
        appdata_p.set_defaults(func=self.action_appdata)
        appdata_p.add_argument("action", choices=("get", "put"), help="Action")
        appdata_p.add_argument("host", help="Target host")
        appdata_p.add_argument(
            "apps",
            nargs="+",
            metavar="app",
            help="Selected application(s)",
        )
        appdata_p.add_argument(
            "-d",
            "--dir",
            dest="local_dir",
            metavar="path",
            type=_str,
            default=Path("app_data").resolve(),
            help="Path for local data copy (default: %(default)s)",
        )

        bootstrap_p = subp.add_parser(
            "bootstrap",
            parents=[ansible_vault_mixin],
            help="Bootstrap new host",
        )
        bootstrap_p.set_defaults(func=self.action_bootstrap, chdir=True)
        bootstrap_p.add_argument("host", help="Target host")
        bootstrap_p.add_argument("username", help="Username on target host")

        run_p = subp.add_parser(
            "run",
            parents=[ansible_mixin, ansible_vault_mixin],
            help="Deploy",
        )
        run_p.set_defaults(func=self.action_run, chdir=True)

        hostvars_p = subp.add_parser(
            "hostvars",
            parents=[ansible_mixin, ansible_vault_mixin],
            help="Print host variables",
        )
        hostvars_p.set_defaults(func=self.action_hostvars, chdir=True)
        hostvars_p.add_argument(
            "-m",
            "--message",
            dest="message",
            metavar="expression",
            default='"{{hostvars[inventory_hostname]}}"',
            help=(
                "Expression for Ansible `debug` module"
                " (default: `%(default)s`)"
            ),
        )

        _args, _extra_args = ap.parse_known_args()
        if not hasattr(_args, "func"):
            ap.print_help()
            sys.exit(1)
        return _args, _extra_args

    @cached_property
    def ansible_collections(self) -> AnsibleCollections:
        return AnsibleCollections(Path() / "requirements.yml")


main = partial(Homestar().main)
