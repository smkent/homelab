import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property, partial

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

        return ap.parse_known_args()

    def run(self, cmd: list[str]) -> None:
        cmd = [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            self.args.service,
        ] + cmd
        run(cmd, dry_run=self.args.dry_run)

    def action_reload_caddy(self) -> None:
        self.run(["caddy", "reload", "--config", "/etc/caddy/Caddyfile"])

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


main = partial(Homeconf().main)
