# Python Style Guide

This document outlines the coding style, conventions, and common patterns for the `python-json-logger` project. Adhering to this guide will help maintain code consistency, readability, and quality.

## General Principles

*   **Readability Counts:** Write code that is easy for others (and your future self) to understand. This aligns with [PEP 20 (The Zen of Python)](https://peps.python.org/pep-0020/).
*   **Consistency:** Strive for consistency in naming, formatting, and structure throughout the codebase.
*   **Simplicity:** Prefer simple, straightforward solutions over overly complex ones.
*   **PEP 8:** Follow [PEP 8 (Style Guide for Python Code)](https://peps.python.org/pep-0008/) for all Python code. The automated tools mentioned below will enforce many of these rules. This guide highlights project-specific conventions or particularly important PEP 8 aspects.

## Formatting and Linting

We use automated tools to enforce a consistent code style and catch potential errors. These include:

*   **Black:** For opinionated code formatting.
*   **Pylint:** For static code analysis and error detection.
*   **MyPy:** For static type checking.

Ensure these tools are run before committing code. Configuration for these tools can be found in `pyproject.toml`, `pylintrc`, and `mypy.ini` respectively. This guide primarily focuses on conventions not automatically verifiable by these tools.

## Imports

Imports should be structured into the following groups, separated by a blank line, and generally alphabetized within each group:

1.  **Future Imports:** e.g., `from __future__ import annotations`
2.  **Standard Library Imports:** e.g., `import sys`, `from datetime import datetime`
3.  **Installed (Third-Party) Library Imports:** e.g., `import pytest`
4.  **Application (Local) Imports:** e.g., `from .core import BaseJsonFormatter` (This project-specific pattern is crucial for internal organization).

## Naming Conventions

While PEP 8 covers most naming, we emphasize:

*   **Modules:** `lowercase_with_underscores.py`
*   **Packages:** `lowercase`
*   **Classes & Type Aliases:** `CapWords` (e.g., `BaseJsonFormatter`, `OptionalCallableOrStr`). This is standard, but explicitly stated for clarity.
*   **Constants:** `UPPERCASE_WITH_UNDERSCORES` (e.g., `RESERVED_ATTRS`). This is a project convention for module-level constants.

(Functions, methods, and variables follow standard PEP 8 `lowercase_with_underscores`).

## Comments

*   Use comments to explain non-obvious code, complex logic, or important design decisions. Avoid comments that merely restate what the code does.
*   For internal code organization within files, especially in longer modules or classes, use comments like `## Section Title ##` or `### Subsection Title ###` to delineate logical blocks of code (e.g., `## Parent Methods ##` as seen in `src/pythonjsonlogger/core.py`). This is distinct from Markdown headings used in this document.

## Docstrings

*   All public modules, classes, functions, and methods **must** have docstrings.
*   We use `mkdocstrings` for generating API documentation, which defaults to the **Google Python Style Guide** for docstrings. Please adhere to this style. You can find the guide [here](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
*   Docstrings should clearly explain the purpose, arguments, return values, and any exceptions raised.
*   **Project Convention:** Use the following markers to indicate changes over time:
    *   `*New in version_number*`: For features added in a specific version.
    *   `*Changed in version_number*`: For changes made in a specific version.
    *   `*Deprecated in version_number*`: For features deprecated in a specific version.

    Example:
    ```python
    def my_function(param1: str, param2: int) -> bool:
        """Does something interesting.

        Args:
            param1: The first parameter, a string.
            param2: The second parameter, an integer.

        Returns:
            True if successful, False otherwise.

        Raises:
            ValueError: If param2 is negative.

        *New in 3.1*
        """
        # ... function logic ...
        return True # See 'Return Statements'
    ```

## Type Hinting

*   All new code **must** include type hints for function arguments, return types, and variables where appropriate, as per PEP 484.
*   Use standard types from the `typing` module.
*   **Project Convention:** For Python versions older than 3.10, use `typing_extensions.TypeAlias` for creating type aliases. For Python 3.10+, use `typing.TypeAlias` (e.g., `OptionalCallableOrStr: TypeAlias = ...`).

## Return Statements

*   **Project Convention:** All functions and methods **must** have an explicit `return` statement.
*   If a function does not logically return a value, it should end with `return None` or simply `return`. This makes the intent clear and consistent across the codebase.

    Example:
    ```python
    def process_data(data: dict) -> None:
        """Processes the given data."""
        # ... processing logic ...
        print(data)
        return # or return None
    ```

## Class Structure

*   Group methods logically within a class (e.g., initialization, public, protected/private, special methods).
*   The use of internal code comments like `## Parent Methods ##` (as seen in `src/pythonjsonlogger/core.py`) is encouraged for readability in complex classes.

## Project-Specific Code Patterns and Idioms

Familiarize yourself with these patterns commonly used in this project:

*   **Version-Specific Logic:** Using `sys.version_info` for compatibility:
    ```python
    if sys.version_info >= (3, 10):
        # Python 3.10+ specific code
    else:
        # Code for older versions
    ```
*   **Type Aliases for Clarity:** As mentioned in Type Hinting, using `TypeAlias` for complex type combinations improves readability.
*   **Custom Exceptions:** Defining custom exception classes for application-specific error conditions (e.g., `MissingPackageError` in `src/pythonjsonlogger/exception.py`).
*   **Helper/Utility Functions:** Encapsulating reusable logic in utility modules (e.g., functions in `src/pythonjsonlogger/utils.py`).
*   **Conditional Imports for Optional Dependencies:** The pattern in `src/pythonjsonlogger/__init__.py` for checking optional dependencies like `orjson` and `msgspec` using `package_is_available` from `utils.py`.

## Testing

This project uses `pytest` for testing. Adherence to good testing practices is crucial.

*   **Test Location:** Tests are located in the `tests/` directory.
*   **Test Naming:** Test files `test_*.py`; test functions `test_*`.
*   **Fixtures:** Utilize `pytest` fixtures (`@pytest.fixture`) for setup.
    *   **Project Pattern:** The `LoggingEnvironment` dataclass and `env` fixture in `tests/test_formatters.py` is a key pattern for testing logger behavior. Adapt this for similar scenarios.
*   **Parametrization:** Use `@pytest.mark.parametrize` extensively to cover multiple scenarios efficiently.
*   **Clarity and Focus:** Each test should be focused and its name descriptive.
*   **Assertions:** Use clear, specific `pytest` assertions.

By following these guidelines, we can ensure that `python-json-logger` remains a high-quality, maintainable, and developer-friendly library.
