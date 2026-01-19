# Homelab

[![Build](https://img.shields.io/github/checks-status/smkent/homelab/main?label=build)][gh-actions]
[![codecov](https://codecov.io/gh/smkent/homelab/branch/main/graph/badge.svg)][codecov]
[![GitHub stars](https://img.shields.io/github/stars/smkent/homelab?style=social)][repo]

Self-hosted apps I run on my [homelab][homelab] and personal infrastructure.
Deployments are managed by [Ansible][ansible].

# New machine first steps

Before using this repository, perform these steps on the target machine.

## Operating system installation

### [Linode][linode]

Select [Debian][debian] 13 (or the current stable version) when creating a new
Linode instance.

### Home server

Install [Debian stable][debian] using the [netinst][debian-netinst] installer
media.

* In the disk partitioner, choose "encrypted LVM" to encrypt the entire disk.
* The installer requires creation of an unprivileged user. This user should be
  manually deleted after installation, so choose a simple temporary username.

## First-run configuration

Use `homestar bootstrap` to automatically remove the unprivileged user created
during installation and replace it with the expected deployment user.

# Deployment

If not already present, add the target machine's hostname to
`ansible/hosts.yml`.

Use `homestar` to set up one or more target machine(s). Command line options
include inventory and playbook file selection. Additional arguments are passed
through to [ansible-playbook][ansible-playbook-docs].

## Invocation examples

* Deploy to a single host (dry run): `homestar run -C -l target-host-name`
* Deploy to a single host: `homestar run -l target-host-name`
* Deploy to all configured hosts (dry run): `homestar run -C`
* Deploy to all configured hosts: `homestar run`

# Development

## [Poetry][poetry] installation

Via [`pipx`][pipx]:

```console
pip install pipx
pipx install poetry
pipx inject poetry poetry-pre-commit-plugin
```

Via `pip`:

```console
pip install poetry
poetry self add poetry-pre-commit-plugin
```

## Development tasks

* Setup: `poetry install`
* Run static checks: `poetry run poe lint` or
  `poetry run pre-commit run --all-files`
* Run static checks and tests: `poetry run poe test`

---

Created from [smkent/cookie-python][cookie-python] using
[cookiecutter][cookiecutter]

[ansible-playbook-docs]: https://docs.ansible.com/ansible/latest/cli/ansible-playbook.html
[ansible]: https://docs.ansible.com/ansible/latest/
[codecov]: https://codecov.io/gh/smkent/homelab
[cookie-python]: https://github.com/smkent/cookie-python
[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[debian-netinst]: https://www.debian.org/distrib/netinst
[debian]: https://www.debian.org/releases/stable/
[gh-actions]: https://github.com/smkent/homelab/actions?query=branch%3Amain
[homelab]: https://web.archive.org/web/20221023001900/https://linuxhandbook.com/homelab/
[linode]: https://linode.com
[pipx]: https://pypa.github.io/pipx/
[poetry]: https://python-poetry.org/docs/#installation
[repo]: https://github.com/smkent/homelab
