# Contributing

Contributions are welcome!

## Code of Conduct

In general we follow the [Python Software Foundation Code of Conduct](https://policies.python.org/python.org/code-of-conduct/).

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

We don't have styling documentation, so where possible try to match existing code. This includes the use of "headings" and "dividers" (this will make sense when you look at the code).

All devlopment tooling can be installed (usually into a virtual environment), using the `dev` optiontal dependency:

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

If making changes to the documentation you can preview the changes locally using `mkdocs`. Changes to the README can be previewed using [`grip`](https://github.com/joeyespo/grip) (not included in `dev` dependencies).

```shell
mkdocs serve
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

Once you've submitted your pull request make sure that all CI jobs are passing. Pull requests will failing jobs will not be reviewed.

### 5. Code review

Your code will be reviewed by a maintainer.

If you're not familiar with code review start by reading [this guide](https://google.github.io/eng-practices/review/).

!!! tip "Remember you are not your work"

    You might be asked to explain or justify your choices. This is not a criticism of your value as a person!

    Often this is because there are multiple ways to solve the same problem and the reviewer would like to understand more about the way you solved.

## Common Topics

### Adding a new encoder

New encoders may be added, however how popular / common a library is will be taken into consideration before being added.

### Versioning and breaking compatability

This project uses semantic versioning.

In general backwards compatability is always preferred. This library is widely used and not particularly sophisticated, there must be a good reason for breaking changes.

### Spelling

The original implementation of this project used US spelling so it will continue to use US spelling for all code.

Documentation is more flexible and may use a variety of English spellings.
