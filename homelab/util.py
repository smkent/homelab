import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def run(
    cmd: Sequence[str],
    *,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    **kwargs: Any,
) -> Any:
    kwargs.setdefault("check", True)
    print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)  # noqa: T201
    if not dry_run:
        return subprocess.run(cmd, env=os.environ | (env or {}), **kwargs)  # noqa: PLW1510, S603
    return None


@contextmanager
def gpg_fifo(vault: Path) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as td:
        fifo = Path(td) / "ansible.fifo"
        os.mkfifo(fifo, 0o0600)
        cmd = f"gpg -d {vault} > {fifo}"
        print("+", cmd, file=sys.stderr)  # noqa: T201
        p = subprocess.Popen(cmd, shell=True)  # noqa: S602
        try:
            yield fifo
        finally:
            p.terminate()
            p.wait()
