import socket
import subprocess
import sys
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property, wraps
from pathlib import Path
from typing import Annotated, Any

from typer import Argument, Context, Option, Typer

from .app import CLIError, HomelabCLIApp
from .pg import PostgresConfig
from .stack import ComposeStack
from .util import run


@dataclass
class HomerunBase:
    dry_run: bool = False
    service: str | None = None
    stack: ComposeStack = field(default_factory=ComposeStack)

    @cached_property
    def pg(self) -> PostgresConfig:
        if not self.service:
            raise CLIError("Service name is required")
        return PostgresConfig(service_name=self.service, dry_run=self.dry_run)

    def run(
        self,
        cmd: list[str],
        exec: bool = False,
        exec_args: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if not self.service:
            raise Exception("service is required")
        if exec:
            action_cmd = ["exec"] + (
                exec_args if exec_args is not None else ["-i"]
            )
        else:
            action_cmd = ["run", "--rm", "--no-deps", "--quiet"]
        cmd = ["docker", "compose"] + action_cmd + [self.service] + cmd
        run(cmd, dry_run=self.dry_run, **kwargs)


@dataclass
class StackAppDir:
    stack: str | None = None
    service: str | None = None

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def _wrapper(ctx: Context, *args: Any, **kwargs: Any) -> Any:
            stack = self.stack or kwargs.get("stack")
            ctx.obj.service = self.service or kwargs.get("service")
            with ctx.obj.stack.app_stack(stack) if stack else nullcontext():
                return func(ctx, *args, **kwargs)

        return _wrapper


@dataclass
class Homerun(HomelabCLIApp):
    cli = Typer(
        help="Perform configured administration actions",
        add_completion=False,
        no_args_is_help=True,
        pretty_exceptions_enable=False,
        rich_markup_mode=None,
    )

    @classmethod
    def app(cls) -> None:
        try:
            super().app()
        except subprocess.CalledProcessError as e:
            print(f"{e.__class__.__name__}: {e}", file=sys.stderr)

    @cli.callback()
    @staticmethod
    def setup(
        ctx: Context,
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
        ctx.obj = HomerunBase(dry_run=dry_run)

    @cli.command(help="Render and validate Authelia configuration template")
    @StackAppDir("login", "authelia")
    @staticmethod
    def aconf(ctx: Context) -> None:
        for action in ["template", "validate"]:
            ctx.obj.run(
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

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
        help="Repeat `docker compose` commands for all enabled apps",
    )
    @staticmethod
    def dcp(
        ctx: Context,
        apps: Annotated[
            list[str],
            Option(
                "-a",
                "--app",
                metavar="app",
                default_factory=list,
                show_default="all apps",
                help=(
                    "Run command on the specified app,"
                    " instead of all enabled apps"
                ),
            ),
        ],
    ) -> None:
        dcp_args = []
        for arg in ctx.args:
            if arg.startswith("@") and len(arg) > 1:
                if (app := arg[1:]) not in apps:
                    apps.append(app)
                continue
            dcp_args.append(arg)
        if not dcp_args:
            return
        for i, app_dir in enumerate(ctx.obj.stack.each_host_app_dir(apps)):
            if i:
                print()
            print(f">>> {app_dir}")
            run(["docker", "compose"] + dcp_args, dry_run=ctx.obj.dry_run)

    @cli.command(help="Create PBKDF2 hash of input OIDC client secret")
    @StackAppDir("login", "authelia")
    @staticmethod
    def hashoidc(ctx: Context) -> None:
        ctx.obj.run(
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

    @cli.command(
        help="Install, authenticate, and start a shell with lldap-cli"
    )
    @StackAppDir("login", "lldap")
    @staticmethod
    def lldapcli(ctx: Context) -> None:
        ctx.obj.run(
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

    @cli.command(help="Generate OIDC client ID and secret for new OIDC client")
    @StackAppDir("login", "authelia")
    @staticmethod
    def mkoidc(ctx: Context) -> None:
        ctx.obj.run(
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
        ctx.obj.run(
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

    @cli.command(help="Flush cached Nextcloud OIDC provider info")
    @StackAppDir("nextcloud", "nextcloud")
    @staticmethod
    def ncflush(ctx: Context) -> None:
        for var in ["well-known", "last_updated_well_known"]:
            ctx.obj.run(["php", "occ", "config:app:delete", "oidc_login", var])

    @cli.command(help="Dump Postgres database to file")
    @StackAppDir(None, "db")
    @staticmethod
    def pgdump(
        ctx: Context,
        stack: Annotated[str, Argument(metavar="stack", help="App stack")],
        dump_file: Annotated[
            Path, Option("-f", "--file", metavar="file", help="Dump file")
        ] = Path("./pg_dump.sql"),
    ) -> None:
        if dump_file.exists():
            raise CLIError(f"{dump_file.resolve()} already exists")
        with (
            open(dump_file, "w") if not ctx.obj.dry_run else nullcontext()
        ) as f:
            ctx.obj.run(
                ["pg_dumpall", "-U", ctx.obj.pg.admin_user],
                exec=True,
                stdout=f,
            )

    @cli.command(help="Upgrade PostgreSQL major version")
    @StackAppDir(None, "db")
    @staticmethod
    def pgupgrade(
        ctx: Context,
        stack: Annotated[str, Argument(metavar="stack", help="App stack")],
        dump_file: Annotated[
            Path, Option("-f", "--file", metavar="file", help="Dump file")
        ] = Path("./pg_dump.sql"),
        version: Annotated[
            int,
            Option(
                "-V",
                "--version",
                metavar="version",
                help="Target PostgreSQL major version number",
            ),
        ] = 18,
    ) -> None:
        def _is_container_up() -> bool:
            return bool(
                run(
                    ["docker", "compose", "ps", "-q", ctx.obj.service],
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout
            )

        def _start_container() -> None:
            print(f"Starting {ctx.obj.service} container")
            run(
                ["docker", "compose", "up", "--wait", ctx.obj.service],
                dry_run=ctx.obj.dry_run,
            )

        def _stop_container() -> None:
            print(f"Stopping {ctx.obj.service} container")
            run(
                ["docker", "compose", "down", ctx.obj.service],
                dry_run=ctx.obj.dry_run,
            )

        if dump_file.exists():
            raise CLIError(f"{dump_file.resolve()} already exists")
        pg = ctx.obj.pg
        if (
            new_data_dir := pg.source_volume.resolve().parent
            / f"postgres{version}"
        ).exists():
            raise CLIError(f"{new_data_dir.resolve()} already exists")
        if pg.version >= version:
            raise CLIError(
                f"No upgrade needed for current version {pg.version}"
            )
        if pg.source_volume.resolve() == new_data_dir.resolve():
            raise CLIError(
                "Source and target volumes are the same: "
                + pg.source_volume.resolve()
            )
        if not _is_container_up():
            _start_container()
        print(f"Dumping existing database data to {dump_file}")
        Homerun.pgdump(ctx, stack, dump_file)
        _stop_container()
        print("Updating container configuration")
        pg.set_version(version)
        pg.set_volume_source(new_data_dir.name)
        run(
            ["git", "--no-pager", "diff", "--", str(pg.compose_file)],
            dry_run=ctx.obj.dry_run,
        )
        _start_container()
        print("Importing dumped database data")
        with open(dump_file) if not ctx.obj.dry_run else nullcontext() as f:
            ctx.obj.run(
                ["psql", "-U", pg.admin_user, "-d", pg.admin_database],
                exec=True,
                exec_args=["-T"],
                stdin=f,
            )
        print("Upgrade complete")

    @cli.command(help="Interact with PostgreSQL")
    @StackAppDir(None, "db")
    @staticmethod
    def psql(
        ctx: Context,
        stack: Annotated[str, Argument(metavar="stack", help="App stack")],
    ) -> None:
        pg = ctx.obj.pg
        ctx.obj.run(
            ["psql", "-U", pg.admin_user, "-d", pg.admin_database], exec=True
        )

    @cli.command(help="Reload Caddy from current Caddyfile")
    @StackAppDir("gateway", "caddy")
    @staticmethod
    def reloadcaddy(ctx: Context) -> None:
        ctx.obj.run(
            ["caddy", "reload", "--config", "/etc/caddy/Caddyfile"],
            exec=True,
        )

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
        help="Run restic commands with preconfigured settings",
    )
    @StackAppDir("backrest", "backrest")
    @staticmethod
    def restic(
        ctx: Context,
        repository: Annotated[
            str,
            Option(
                "-r",
                "--repo",
                metavar="name",
                help="Repository name",
            ),
        ] = socket.gethostname().split(".", 1)[0],
        restore_target: Annotated[
            Path | None,
            Option(
                "-t",
                "--target",
                metavar="directory",
                show_default="none",
                exists=True,
                file_okay=False,
                dir_okay=True,
                resolve_path=True,
                help="Restore target",
            ),
        ] = None,
        rw: Annotated[
            bool,
            Option(
                "--rw",
                help="Mount repository read-write and enable locking",
            ),
        ] = False,
    ) -> None:
        if not Path(repository).is_absolute():
            repository = f"/backup/{repository}"
        mountflags = "rw" if rw else "ro"
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{Path.home() / 'backup'}:/backup:{mountflags}",
            "-v",
            (
                f"{Path('../../secrets/restic-password').resolve()}"
                ":/run/secrets/restic-password"
            ),
        ]
        if restore_target:
            cmd += ["-v", f"{restore_target}:/restore_target:rw"]
        if rw:
            cmd += ["--user", "1000:1000"]
        cmd += [
            "restic/restic",
            "-p",
            "/run/secrets/restic-password",
            "-r",
            repository,
        ]
        if not rw:
            cmd += ["--no-lock"]
        cmd += ctx.args
        if restore_target:
            cmd += ["--target", "/restore_target"]
        run(cmd)
