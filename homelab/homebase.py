import argparse
import subprocess
import sys
from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property, partial
from pathlib import Path
from typing import Any

from .pg import PG
from .stack import ComposeStack
from .util import run


@dataclass
class Homebase:
    stack: ComposeStack = field(default_factory=ComposeStack)

    def main(self) -> None:
        with self.stack.app(self.args.stack):
            self.args.func()

    @cached_property
    def args(self) -> argparse.Namespace:
        return self._args[0]

    @cached_property
    def extra_args(self) -> Sequence[str]:
        return self._args[1]

    @cached_property
    def _args(self) -> tuple[argparse.Namespace, Sequence[str]]:
        ap = argparse.ArgumentParser(
            description=("Perform configured administration actions"),
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
        reloadcaddy_p = subp.add_parser(
            "reloadcaddy",
            help="Reload Caddy from current Caddyfile",
        )
        reloadcaddy_p.set_defaults(
            func=self.action_reload_caddy, stack="gateway", service="caddy"
        )
        aconf_p = subp.add_parser(
            "aconf",
            help="Render and validate Authelia configuration template",
        )
        aconf_p.set_defaults(
            func=self.action_aconf, stack="login", service="authelia"
        )
        lldap_cli_p = subp.add_parser(
            "lldapcli",
            help="Install, authenticate, and start a shell with lldap-cli",
        )
        lldap_cli_p.set_defaults(
            func=self.action_lldap_cli, stack="login", service="lldap"
        )
        mkoidc_p = subp.add_parser(
            "mkoidc",
            help="Generate OIDC client ID and secret for new OIDC client",
        )
        mkoidc_p.set_defaults(
            func=self.action_mkoidc, stack="login", service="authelia"
        )
        hashoidc_p = subp.add_parser(
            "hashoidc", help="Create PBKDF2 hash of input OIDC client secret"
        )
        hashoidc_p.set_defaults(
            func=self.action_hashoidc, stack="login", service="authelia"
        )
        ncflush = subp.add_parser(
            "ncflush",
            help="Flush cached Nextcloud OIDC provider info",
        )
        ncflush.set_defaults(
            func=self.action_ncflush,
            stack="nextcloud",
            service="nextcloud",
        )

        pg_mixin = argparse.ArgumentParser(add_help=False)
        pg_mixin.add_argument("stack", metavar="stack", help="App stack")

        psql_p = subp.add_parser(
            "psql", parents=[pg_mixin], help="Interact with Postgres"
        )
        psql_p.set_defaults(func=self.action_psql, service="db")

        pgdump_p = subp.add_parser(
            "pgdump", parents=[pg_mixin], help="Dump Postgres database to file"
        )
        pgdump_p.set_defaults(func=self.action_pgdump, service="db")
        pgdump_p.add_argument(
            "-f",
            "--file",
            dest="dump_file",
            metavar="file",
            default="./pg_dump.sql",
            help="Dump file (default: %(default)s)",
        )

        pgupgrade_p = subp.add_parser(
            "pgupgrade",
            parents=[pg_mixin],
            help="Upgrade PostgreSQL major version",
        )
        pgupgrade_p.set_defaults(func=self.action_pgupgrade, service="db")
        pgupgrade_p.add_argument(
            "-f",
            "--file",
            dest="dump_file",
            metavar="file",
            default="./pg_dump.sql",
            help="Dump file (default: %(default)s)",
        )
        pgupgrade_p.add_argument(
            "-V",
            "--version",
            dest="version",
            metavar="version",
            type=int,
            default=18,
            help=(
                "Target PostgreSQL major version number (default: %(default)s)"
            ),
        )

        _args, _extra_args = ap.parse_known_args()
        if not hasattr(_args, "func"):
            ap.print_help()
            sys.exit(1)
        return _args, _extra_args

    def run(
        self,
        cmd: list[str],
        exec: bool = False,
        exec_args: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if exec:
            action_cmd = ["exec"] + (
                exec_args if exec_args is not None else ["-i"]
            )
        else:
            action_cmd = ["run", "--rm", "--no-deps"]
        cmd = ["docker", "compose"] + action_cmd + [self.args.service] + cmd
        run(cmd, dry_run=self.args.dry_run, **kwargs)

    def action_reload_caddy(self) -> None:
        self.run(
            ["caddy", "reload", "--config", "/etc/caddy/Caddyfile"], exec=True
        )

    def action_lldap_cli(self) -> None:
        self.run(
            [
                "sh",
                "-c",
                (
                    "apk update"
                    " && apk add util-linux"
                    " && curl -s https://raw.githubusercontent.com/Zepmann/lldap-cli/refs/heads/main/lldap-cli > /bin/lldap-cli"  # noqa: E501
                    " && chmod +x /bin/lldap-cli"
                    " && eval $("
                    "LLDAP_CONFIG=/data/lldap_config.toml"
                    " lldap-cli"
                    " -D admin -w $(cat /run/secrets/lldap-ldap-user-pass)"
                    " login)"
                    " && lldap-cli group list"
                    ' && PATH="${PATH}:/app" sh'
                ),
            ],
            exec=True,
            check=False,
        )

    def action_aconf(self) -> None:
        for action in ["template", "validate"]:
            self.run(
                [
                    "authelia",
                    "--config",
                    "/config/configuration.yml",
                    "--config.experimental.filters",
                    "template",
                    "config",
                    action,
                ]
            )

    def action_hashoidc(self) -> None:
        self.run(
            [
                "authelia",
                "crypto",
                "hash",
                "generate",
                "pbkdf2",
                "--variant",
                "sha512",
            ]
        )

    def action_mkoidc(self) -> None:
        self.run(
            [
                "authelia",
                "crypto",
                "rand",
                "--length",
                "72",
                "--charset",
                "rfc3986",
            ]
        )
        self.run(
            [
                "authelia",
                "crypto",
                "hash",
                "generate",
                "pbkdf2",
                "--variant",
                "sha512",
                "--random",
                "--random.length",
                "72",
                "--random.charset",
                "rfc3986",
            ]
        )

    def action_ncflush(self) -> None:
        for var in ["well-known", "last_updated_well_known"]:
            self.run(["php", "occ", "config:app:delete", "oidc_login", var])

    def action_psql(self) -> None:
        pg = PG()
        self.run(
            ["psql", "-U", pg.admin_user, "-d", pg.admin_database], exec=True
        )

    def action_pgdump(self) -> None:
        dump_file = Path(self.args.dump_file)
        if dump_file.exists():
            raise Exception(f"{dump_file.resolve()} already exists")
        pg = PG()
        with (
            open(dump_file, "w") if not self.args.dry_run else nullcontext()
        ) as f:
            self.run(["pg_dumpall", "-U", pg.admin_user], exec=True, stdout=f)

    def action_pgupgrade(self) -> None:
        def _is_container_up() -> bool:
            return bool(
                run(
                    ["docker", "compose", "ps", "-q", self.args.service],
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout
            )

        def _start_container() -> None:
            print(f"Starting {self.args.service} container")
            run(
                ["docker", "compose", "up", "--wait", self.args.service],
                dry_run=self.args.dry_run,
            )

        def _stop_container() -> None:
            print(f"Stopping {self.args.service} container")
            run(
                ["docker", "compose", "down", self.args.service],
                dry_run=self.args.dry_run,
            )

        dump_file = Path(self.args.dump_file)
        if dump_file.exists():
            raise Exception(f"{dump_file.resolve()} already exists")
        if (
            new_data_dir := Path("data") / f"postgres{self.args.version}"
        ).exists():
            raise Exception(f"{new_data_dir.resolve()} already exists")
        pg = PG(dry_run=self.args.dry_run)
        if pg.source_volume.resolve() == new_data_dir.resolve():
            raise Exception(
                "Source and target volumes are the same:",
                pg.source_volume.resolve(),
            )
        if not _is_container_up():
            _start_container()
        print(f"Dumping existing database data to {dump_file}")
        self.action_pgdump()
        _stop_container()
        print("Updating container configuration")
        pg.set_version(self.args.version)
        pg.set_volume_source(new_data_dir.resolve())
        run(
            ["git", "--no-pager", "diff", "--", "compose.yaml"],
            dry_run=self.args.dry_run,
        )
        _start_container()
        print("Importing dumped database data")
        with open(dump_file) if not self.args.dry_run else nullcontext() as f:
            self.run(
                ["psql", "-U", pg.admin_user],
                exec=True,
                exec_args=["-T"],
                stdin=f,
            )
        print("Upgrade complete")


main = partial(Homebase().main)
