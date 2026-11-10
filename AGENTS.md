# Contributing with an AI tool

Before making changes, read [the contributing guide](docs/contributing.md),
especially its [Generative AI Policy](docs/contributing.md#generative-ai-policy),
and the [Python style guide](docs/style-guide.md). These documents are the
authoritative contribution requirements; this file is only a starting point.

AI-assisted contributions require human supervision and a human who takes legal
and technical responsibility for the work. Follow the policy's requirements for
human communication and AI disclosure. Do not submit work that the human
contributor cannot explain and defend.

## Project layout

- `src/pythonjsonlogger/`: the formatters and shared formatting/encoding helpers.
- `tests/`: pytest tests, including formatter tests and logging fixtures.
- `docs/`: documentation, contribution policies, and the changelog.
- `benchmarks/`: opt-in formatter and serialization benchmarks.

## Development

Install development dependencies with `uv sync --group dev`. Run commands from
the repository root using `uv run`:

```sh
uv run black src tests
uv run pylint --output-format=colorized src
uv run pyrefly check src tests
uv run pytest
```

See the contributing guide for the PR checklist, including when to update the
version, changelog, tests, and docstrings. See `tox.ini` for the complete test,
lint, formatting, and benchmark environments.
