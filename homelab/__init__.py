"""Self-hosted apps I run on my homelab and personal infrastructure. Deployments are managed by Ansible."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as import_version

try:
    version = import_version(__name__)
except PackageNotFoundError:  # pragma: no cover
    version = "0.0.0"
