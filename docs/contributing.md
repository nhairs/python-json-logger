# Contributing

Contributions are welcome!

## Code of Conduct

In general we follow the [Python Software Foundation Code of Conduct](https://policies.python.org/python.org/code-of-conduct/). Please note that we are not affiliated with the PSF.

## Pull Request Process

**0. Before you begin**

If you're not familiar with contributing to open source software, [start by reading this guide](https://opensource.guide/how-to-contribute/).

Be aware that anything you contribute will be licenced under [the project's licence](https://github.com/nhairs/python-json-logger/blob/main/LICENSE). If you are making a change as a part of your job, be aware that your employer might own your work and you'll need their permission in order to licence the code.

### 1. Find something to work on

Where possible it's best to stick to established issues where discussion has already taken place. Contributions that haven't come from a discussed issue are less likely to be accepted.

The following are things that can be worked on without an existing issue:

- Updating documentation. This includes fixing in-code documentation / comments, and the overall docs.
- Small changes that don't change functionality such as refactoring or adding / updating tests.

### 2. Fork the repository and make your changes

#### Coding Style

Before writing any code, please familiarize yourself with our [Python Style Guide](style-guide.md). This document outlines our coding conventions, formatting expectations, and common patterns used in the project. Adhering to this guide is crucial for maintaining code consistency and readability.

While the style guide covers detailed conventions, always try to match the style of existing code in the module you are working on, especially regarding local patterns and structure.

#### Development Setup

All devlopment tooling can be installed (usually into a virtual environment), using the `dev` optional dependency:

```shell
pip install -e '.[dev]'`
```

Before creating your pull request you'll want to format your code and run the linters and tests:

```shell
# Format
black src tests

# Lint
pylint --output-format=colorized src
mypy src tests

# Tests
pytest
```

The above commands (`black`, `pylint`, `mypy`, `pytest`) should all be run before submitting a pull request.

If making changes to the documentation you can preview the changes locally using `mkdocs`. Changes to the `README.md` can be previewed using a tool like [`grip`](https://github.com/joeyespo/grip) (installable via `pip install grip`).

```shell
mkdocs serve
# For README preview (after installing grip):
# grip
```

!!! note
    In general we will always squash merge pull requests so you do not need to worry about a "clean" commit history.

### 3. Checklist

Before pushing and creating your pull request, you should make sure you've done the following:

- Updated any relevant tests.
- Formatted your code and run the linters and tests.
- Updated the version number in `pyproject.toml`. In general using a `.devN` suffix is acceptable.
  This is not required for changes that do no affect the code such as documentation.
- Add details of the changes to the change log (`docs/change-log.md`), creating a new section if needed.
- Add notes for new / changed features in the relevant docstring.

**4. Create your pull request**

When creating your pull request be aware that the title and description will be used for the final commit so pay attention to them.

Your pull request description should include the following:

- Why the pull request is being made
- Summary of changes
- How the pull request was tested - especially if not covered by unit testing.

Once you've submitted your pull request make sure that all CI jobs are passing. Pull requests with failing jobs will not be reviewed.

### 5. Code review

Your code will be reviewed by a maintainer.

If you're not familiar with code review start by reading [this guide](https://google.github.io/eng-practices/review/).

!!! tip "Remember you are not your work"

    You might be asked to explain or justify your choices. This is not a criticism of your value as a person!

    Often this is because there are multiple ways to solve the same problem and the reviewer would like to understand more about the way you solved.

## Common Topics

### Adding a new encoder

New encoders may be added depending on their popularity. Only encoders [in the top 1000 packages](https://hugovk.github.io/top-pypi-packages/) or with monthly downloads exceeding 10M/month will be considered.

You must open an issue before creating a pull request.

For examples of how to support a third-party encoder see `orjson.py` and `msgspec.py`.

The following encoders have been considered and rejected:

- [simplejson](https://github.com/simplejson/simplejson) - as of 2026-03-29 is ranked ~370 with ~55M downloads / month. Due to errors when handling `bytes` objects and lack of interest from the community ([see comment for more details](https://github.com/nhairs/python-json-logger/pull/64#issuecomment-4149326316)).
- [ultrajson](https://github.com/ultrajson/ultrajson) (`usjon`) - as of 2026-03-29 is ranked ~630 with ~27 downloads / month. Due to errors when handling `bytes` objects and lack of interest from the community ([see comment for more details](https://github.com/nhairs/python-json-logger/pull/64#issuecomment-4149326316)). Additionally it is in maintence mode.
- [python-rapidjson](https://github.com/python-rapidjson/python-rapidjson) - as of 2026-03-22 is ranked ~1800 with ~4.5M downloads / month.
- [pysimdjson](https://github.com/TkTech/pysimdjson) - as of 2026-03-22 is ranked ~4200 with >1M downloads / month.
- [yapic.json](https://github.com/zozzz/yapic.json) - as of 2026-03-22 is not in top 15K packages.
- [cysimdjson](https://github.com/TeskaLabs/cysimdjson) - as of 2026-03-22 is not in top 15K packages.

### Versioning and breaking compatability

This project uses semantic versioning.

In general backwards compatability is always preferred. This library is widely used and not particularly sophisticated and as such there must be a good reason for breaking changes.

Feature changes MUST be compatible with all [security supported versions of Python](https://endoflife.date/python) and SHOULD be compatible with all unsupported versions of Python where [recent downloads over the last 90 days exceeds 5% of all downloads](https://pypistats.org/packages/python-json-logger).

In general, only the latest `major.minor` version of Python JSON Logger is supported. Bug fixes and feature backports requiring a version branch may be considered but must be discussed with the maintainers first.

See also [Security Policy](security.md).

### Spelling

The original implementation of this project used US spelling so it will continue to use US spelling for all code.

Documentation is more flexible and may use a variety of English spellings.

### Contacting the Maintainers

In general it is preferred to keep communication to GitHub, e.g. through comments on issues and pull requests. If you do need to contact the maintainers privately, please do so using the email addresses in the maintainers section of the `pyproject.toml`.
