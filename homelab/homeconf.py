import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property, partial
from typing import Any

from .stack import ComposeStack
from .util import run


@dataclass
class Homeconf:
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

        return ap.parse_known_args()

    def run(self, cmd: list[str], exec: bool = False, **kwargs: Any) -> None:
        action_cmd = ["exec", "-it"] if exec else ["run", "--rm", "--no-deps"]
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


main = partial(Homeconf().main)
