# Contributing to homelab

**Contributions are welcome!**

Thank you for your time and interest in improving
**homelab**!

## Project resources

* **Repository**: <https://github.com/smkent/homelab>
  for submitting pull requests
* **Issue tracker**: <https://github.com/smkent/homelab/issues>
  for questions or bug reports

## Development documentation

### Prerequisites

- [x] [**git** for version control][git]
- [x] [**mise**][mise] tool manager: `curl https://mise.run | sh` or
  [alternate installation method][mise-installation]

    !!! info

        `mise` ensures additional software is available, such as:

        * A [supported version][python-versions] of [**Python**][python]
        * [Astral's **uv** Python project manager][uv]

[git]: https://git-scm.com
[mise-installation]: https://mise.jdx.dev/installing-mise.html
[mise]: https://mise.jdx.dev
[python-versions]: https://devguide.python.org/versions/
[python]: https://python.org
[uv]: https://docs.astral.sh/uv/

### Project development workflow

#### Cloning the repository

```sh
git clone https://github.com/smkent/homelab
cd homelab
```

Run `mise install` in new repository clones to install tools, dependencies, and
git hooks:

```sh
mise install
```

#### Development tools

* `mise run lint`: Run formatters and static checks
* `mise run test`: Run tests

The `lint` and `test` tasks can also be run as a single combined command with:

```sh
mise run lt
```

### Test snapshots

Some tests compare test results with saved snapshots. Test snapshots can be
updated by running:

```sh
mise run snapup
```

### Applying copier-python template updates

Copier can update your project with template changes that have occurred since
the project was created.

To apply updates, simply run in your project directory:

```sh
copier update
```

This will repeat the setup prompts, in case any prompts have been added or
changed.

!!! tip
    To change template-provided features in your project, simply change your
    answers in the update prompts.

To apply updates without being prompted (reusing all previous answers), run:

```sh
copier update -l
```

When [`copier update`][copier-update] is finished, view changes with
`git status` and `git diff`. Resolve any conflicts, and then commit the result.

[copier-update]: https://copier.readthedocs.io/en/stable/updating/
