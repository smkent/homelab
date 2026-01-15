import argparse
import hashlib
import os
import sys
from collections.abc import Sequence
from contextlib import chdir
from dataclasses import dataclass
from functools import cached_property, partial
from importlib.resources import as_file, files
from pathlib import Path

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
            env=os.environ
            | {
                "ANSIBLE_GALAXY_COLLECTIONS_PATH_WARNING": "false",
                "ANSIBLE_COLLECTIONS_PATHS": str(self.collections.resolve()),
            },
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


class Homerun:
    def main(self) -> None:
        with as_file(files(__package__) / "ansible") as ansible_path:
            print("ansible_path", ansible_path)
            with chdir(ansible_path):
                print(self.args)
                self.args.func()

    def action_hostvars(self) -> None:
        with gpg_fifo(self.args.ansible_vault) as fifo:
            cmd = [
                "ansible",
                "-i",
                f"inventories/{self.args.env}/hosts.yml",
                "-e",
                f"fqdn={self.args.fqdn}",
                "-e",
                f"@{fifo}",
                "-a",
                "msg={{hostvars[inventory_hostname]}}",
                "-m",
                "debug",
                "all",
            ]
            cmd += self.extra_args
            run(cmd)

    def action_run(self) -> None:
        self.ansible_collections.ensure()
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
            with chdir("playbooks"):
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
            "-v",
            "--vault",
            dest="ansible_vault",
            metavar="path",
            type=_str,
            default="vault/ansible.asc",
            help="Path to Ansible vault (default: %(default)s)",
        )

        ap = argparse.ArgumentParser(
            description=(
                "Homelab runner, not to be confused with Homestar Runner"
            ),
        )
        subp = ap.add_subparsers(title="Subcommands", metavar="command")

        run_p = subp.add_parser(
            "run",
            parents=[ansible_mixin, ansible_vault_mixin],
            help="Deploy",
        )
        run_p.set_defaults(func=self.action_run)

        hostvars_p = subp.add_parser(
            "hostvars",
            parents=[ansible_mixin, ansible_vault_mixin],
            help="Print host variables",
        )
        hostvars_p.set_defaults(func=self.action_hostvars)

        return ap.parse_known_args()

    @cached_property
    def ansible_collections(self) -> AnsibleCollections:
        return AnsibleCollections(Path() / "requirements.yml")


main = partial(Homerun().main)
