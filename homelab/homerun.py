from typing import Annotated

from typer import Context, Option, Typer

from .app import HomelabCLIApp
from .stack import ComposeStack
from .util import run


class Homerun(HomelabCLIApp):
    cli = Typer(
        help="Repeat `docker compose` commands for all enabled apps",
        add_completion=False,
        no_args_is_help=True,
        pretty_exceptions_enable=False,
        rich_markup_mode=None,
    )

    @cli.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )
    @staticmethod
    def run(
        ctx: Context,
        apps: Annotated[
            list[str] | None,
            Option(
                "-a",
                "--app",
                metavar="app",
                help=(
                    "Run command on the specified app,"
                    " instead of all enabled apps"
                ),
            ),
        ] = None,
    ) -> None:
        stack = ComposeStack()
        if not ctx.args:
            return
        for i, app_dir in enumerate(stack.each_host_app_dir(apps)):
            if i:
                print()
            print(f">>> {app_dir}")
            run(["docker", "compose"] + ctx.args)
