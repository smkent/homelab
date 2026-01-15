# Homelab

[![Build](https://img.shields.io/github/checks-status/smkent/homelab/main?label=build)][gh-actions]
[![codecov](https://codecov.io/gh/smkent/homelab/branch/main/graph/badge.svg)][codecov]
[![GitHub stars](https://img.shields.io/github/stars/smkent/homelab?style=social)][repo]

Self-hosted apps I run on my [homelab][homelab] and personal infrastructure.
Deployments are managed by [Ansible][ansible].

# New machine first steps

Before using this repository, perform these steps on the target machine.

## [Linode][linode]

Select [Debian][debian] 11 (or the current stable version) when creating a new
Linode instance.

## Home server

Install [Debian stable][debian] using the [netinst][debian-netinst] installer
media.

* In the disk partitioner, choose "encrypted LVM" to encrypt the entire disk.
* The installer requires creation of an unprivileged user. This user should be
  manually deleted after installation, so choose a simple temporary username.

Boot into the new installation and perform these steps:

1. Delete the unprivileged user created during installation:
   `deluser --remove-all-files username`
2. Install basic packages: `apt install -y sudo vim`
3. Create the root user's ssh directory: `mkdir -m 0700 /root/.ssh`
4. Create `/root/.ssh/authorized_keys` with your ssh public key

# Deployment

If not already present, add the target machine's hostname to
`ansible/hosts.yml`.

Use `./deploy` to set up one or more target machine(s). Arguments are passed
through to [ansible-playbook][ansible-playbook-docs].

## Configuration

Environment variables may be set for configuration:

* `ENV`: Inventory file selection. Choices: `live` (default) or `sandbox`.
* `FQDN`: Host suffix domain name, such as `example.com`

## Invocation examples

* Deploy to a single host (dry run): `./deploy -C -l target-host-name`
* Deploy to a single host: `./deploy -l target-host-name`
* Deploy to all configured hosts (dry run): `./deploy -C`
* Deploy to all configured hosts: `./deploy`

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
