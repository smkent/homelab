import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

from typer import Argument, Context, Option, Typer

from ..app import CLIError
from ..util import run

LABEL = "homerun_backup"
MAPPER_NAME = "homerun_backup_disk"
PARTPROBE_TIMEOUT = 5


def sudo_run(cmd: Sequence[str], *args: Any, **kwargs: Any) -> Any:
    return run(["sudo"] + list(cmd), *args, **kwargs)


def mount_mapper_volume(ctx: Context, mount_point: Path | None = None) -> None:
    # Ensure mapper device exists
    if not (
        mapper_dev := Path(f"/dev/mapper/{MAPPER_NAME}")
    ).is_block_device():
        raise CLIError(f"{mapper_dev} not created")
    try:
        fs_label = (
            sudo_run(
                ["lsblk", "-n", "-o", "LABEL", str(mapper_dev)],
                stdout=subprocess.PIPE,
                text=True,
            )
            .stdout.strip()
            .lower()
            or LABEL
        )
        # Verify mount target
        mount_point = mount_point or Path(f"/mnt/{fs_label}")
        if mount_point.is_mount():
            raise CLIError(f"{mount_point} is already mounted")
        if not mount_point.is_dir() and mount_point.parent.is_dir():
            sudo_run(["mkdir", "-v", str(mount_point)])
        if not mount_point.is_dir():
            raise CLIError(f"Mount point {mount_point} does not exist")
        if any(mount_point.iterdir()):
            raise CLIError(f"Mount point {mount_point} is not empty")
        # Mount filesystem
        sudo_run(["mount", str(mapper_dev), str(mount_point)])
        sudo_run(["chown", "-c", "1000:1000", str(mount_point)])
        print(f"Mounted at {mount_point}")
        if current_command_name := ctx.command.name:
            unmount_command = (
                [Path(sys.argv[0]).name]
                + [
                    part
                    for i, part in enumerate(sys.argv[1:])
                    if i < sys.argv.index(current_command_name) - 1
                ]
                + ["unmount"]
            )
            print()
            print(f"When finished, unmount with: {' '.join(unmount_command)}")

    except Exception:
        # Close encrypted volume
        sudo_run(["cryptsetup", "luksClose", MAPPER_NAME])
        raise


class BackupDisk:
    cli = Typer(
        help="Manage external backup disk",
        no_args_is_help=True,
    )

    @cli.command(help="Format new disk")
    @staticmethod
    def format(
        ctx: Context,
        dev: Annotated[
            Path,
            Argument(
                metavar="device",
                readable=False,
                dir_okay=False,
                resolve_path=True,
                help="Block device",
            ),
        ],
        block: Annotated[
            bool,
            Option(
                "--blockdev/--no-blockdev",
                show_default="yes",
                help="Require target to be a block device",
            ),
        ] = True,
        filesystem_label: Annotated[
            str,
            Argument(metavar="label", help="Disk label"),
        ] = LABEL,
        mount_filesystem: Annotated[
            bool,
            Option(
                "--mount/--no-mount",
                show_default="yes",
                help="Mount filesystem after format",
            ),
        ] = True,
    ) -> None:
        if not (is_block := dev.is_block_device()) and block:
            raise CLIError(f"{dev} is not a block device")
        print(f"Format a new disk at {dev}")
        if input(
            f"ALL DATA on {dev} will be LOST! Type {dev} to continue: "
        ) != str(dev):
            sys.exit(1)
        # Check for existing mounts
        try:
            sudo_run(["findmnt", "--source", str(dev)])
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:
                raise
        # Wipe target filesystem headers
        sudo_run(["wipefs", "-a", str(dev)])
        if is_block:
            # Format disk
            sudo_run(
                [
                    "parted",
                    "--script",
                    str(dev),
                    "mklabel",
                    "gpt",
                    "mkpart",
                    "primary",
                    "0%",
                    "100%",
                ]
            )
            # Wait for new partition to appear
            sudo_run(["partprobe", str(dev)])
            start = time.time()
            dev = Path(f"{dev}1")
            while not dev.is_block_device():
                if time.time() - start > PARTPROBE_TIMEOUT:
                    raise CLIError(f"Timeout waiting for {dev} to appear")
                time.sleep(0.1)
        # Create encrypted volume
        sudo_run(
            [
                "cryptsetup",
                "luksFormat",
                "--type",
                "luks2",
                "--cipher",
                "aes-xts-plain64",
                "--key-size",
                "512",
                "--pbkdf",
                "argon2id",
                "--pbkdf-memory",
                "2097152",
                "--pbkdf-parallel",
                "4",
                "--iter-time",
                "5000",
                "--hash",
                "sha512",
                str(dev),
            ]
        )
        # Open encrypted volume
        sudo_run(["cryptsetup", "luksOpen", str(dev), MAPPER_NAME])
        # Ensure mapper device exists
        if not (
            mapper_dev := Path(f"/dev/mapper/{MAPPER_NAME}")
        ).is_block_device():
            raise CLIError(f"{mapper_dev} not created")
        # Create filesystem
        sudo_run(["mkfs.ext4", "-m", "0", "-L", LABEL, str(mapper_dev)])
        if mount_filesystem:
            mount_mapper_volume(ctx)
        else:
            # Close encrypted volume
            sudo_run(["cryptsetup", "luksClose", MAPPER_NAME])

    @cli.command(help="Mount disk")
    @staticmethod
    def mount(
        ctx: Context,
        dev: Annotated[
            Path,
            Argument(
                metavar="device",
                readable=False,
                dir_okay=False,
                resolve_path=True,
                help="Block device",
            ),
        ],
        mount_point: Annotated[
            Path | None,
            Argument(
                metavar="directory",
                readable=False,
                file_okay=False,
                dir_okay=True,
                resolve_path=True,
                show_default=(
                    f"/mnt/[DISK_LABEL] or /mnt/{LABEL} if empty label"
                ),
                help="Mount point",
            ),
        ] = None,
    ) -> None:
        # Check if mapper device exists
        if (mapper_dev := Path(f"/dev/mapper/{MAPPER_NAME}")).exists():
            raise CLIError(f"{mapper_dev} already exists")
        # Open encrypted volume
        sudo_run(["cryptsetup", "luksOpen", str(dev), MAPPER_NAME])
        mount_mapper_volume(ctx, mount_point=mount_point)

    @cli.command(help="Unmount disk")
    @staticmethod
    def unmount(
        ctx: Context,
        mapper: Annotated[
            str, Argument(metavar="name", help="Mapper device name")
        ] = MAPPER_NAME,
    ) -> None:
        # Check if mapper device exists
        if not (mapper_dev := Path(f"/dev/mapper/{MAPPER_NAME}")).exists():
            return
        # Locate mount point
        mount_point = Path(
            sudo_run(
                [
                    "findmnt",
                    "-n",
                    "--output",
                    "TARGET",
                    "--source",
                    str(mapper_dev),
                ],
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()
        )
        if not mount_point.is_mount():
            raise CLIError(f"Detected {mount_point} is not a mount point")
        if not mount_point.is_dir():
            raise CLIError(f"Detected {mount_point} is not a directory")
        # Unmount filesystem
        sudo_run(["umount", str(mapper_dev)])
        # Close encrypted volume
        sudo_run(["cryptsetup", "luksClose", MAPPER_NAME])
        # Check mount point directory is empty
        if any(mount_point.iterdir()):
            raise CLIError(f"Mount point {mount_point} is not empty")
        # Remove mount point directory
        sudo_run(["rmdir", "-v", str(mount_point)])

    # Alias for unmount
    cli.command(name="umount", hidden=True)(unmount)
