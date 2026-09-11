# homelab

Self-hosted apps I run on my [homelab][homelab] and personal infrastructure.
Deployments are managed by [Ansible][ansible].

[![License](https://img.shields.io/github/license/smkent/homelab)](https://github.com/smkent/homelab/blob/main/LICENSE)
[![CI](https://github.com/smkent/homelab/actions/workflows/ci.yaml/badge.svg)](https://github.com/smkent/homelab/actions/workflows/ci.yaml)
[![Coverage](https://codecov.io/gh/smkent/homelab/branch/main/graph/badge.svg)](https://codecov.io/gh/smkent/homelab)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://renovatebot.com)
[![GitHub stars](https://img.shields.io/github/stars/smkent/homelab?style=social)](https://github.com/smkent/homelab)

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

# Project template

This project is generated and maintained with [copier-python][copier-python].

[ansible-playbook-docs]: https://docs.ansible.com/ansible/latest/cli/ansible-playbook.html
[ansible]: https://docs.ansible.com/ansible/latest/
[copier-python]: https://smkent.github.io/copier-python
[debian-netinst]: https://www.debian.org/distrib/netinst
[debian]: https://www.debian.org/releases/stable/
[homelab]: https://web.archive.org/web/20221023001900/https://linuxhandbook.com/homelab/
[linode]: https://linode.com
