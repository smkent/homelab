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
    env: dict[str, str] | None = None,
    **kwargs: Any,
) -> Any:
    kwargs.setdefault("check", True)
    print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    subprocess.run(
        cmd,
        env=os.environ | {"ANSIBLE_NOCOWS": "true"} | (env or {}),
        **kwargs,
    )


@contextmanager
def gpg_fifo(vault: Path) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as td:
        fifo = Path(td) / "ansible.fifo"
        os.mkfifo(fifo, 0o0600)
        cmd = f"gpg -d {vault} > {fifo}"
        print("+", cmd, file=sys.stderr)
        p = subprocess.Popen(cmd, shell=True)  # nosec
        try:
            yield fifo
        finally:
            p.terminate()
            p.wait()
