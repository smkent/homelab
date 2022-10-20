# Homelab

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

[ansible]: https://docs.ansible.com/ansible/latest/
[ansible-playbook-docs]: https://docs.ansible.com/ansible/latest/cli/ansible-playbook.html
[debian-netinst]: https://www.debian.org/distrib/netinst
[debian]: https://www.debian.org/releases/stable/
[homelab]: https://web.archive.org/web/20221023001900/https://linuxhandbook.com/homelab/
[linode]: https://linode.com
