# Python Style Guide

This document outlines the coding style, conventions, and common patterns for the `python-json-logger` project. Adhering to this guide will help maintain code consistency, readability, and quality.

## General Principles

*   **Readability Counts:** Write code that is easy for others (and your future self) to understand.
*   **Consistency:** Strive for consistency in naming, formatting, and structure throughout the codebase.
*   **Simplicity:** Prefer simple, straightforward solutions over overly complex ones.

## Formatting and Linting

We use automated tools to enforce a consistent code style and catch potential errors. These include:

*   **Black:** For opinionated code formatting.
*   **Pylint:** For static code analysis and error detection.
*   **MyPy:** For static type checking.

Ensure these tools are run before committing code. Configuration for these tools can be found in `pyproject.toml`, `pylintrc`, and `mypy.ini` respectively. This guide does not repeat rules enforced by these tools but focuses on conventions not automatically verifiable.

## Imports

Imports should be structured into the following groups, separated by a blank line:

1.  **Future Imports:** e.g., `from __future__ import annotations`
2.  **Standard Library Imports:** e.g., `import sys`, `from datetime import datetime`
3.  **Installed (Third-Party) Library Imports:** e.g., `import pytest`
4.  **Application (Local) Imports:** e.g., `from .core import BaseJsonFormatter`

Within each group, imports should generally be alphabetized.

## Naming Conventions

*   **Modules:** `lowercase_with_underscores.py`
*   **Packages:** `lowercase`
*   **Classes:** `CapWords` (e.g., `BaseJsonFormatter`)
*   **Type Aliases:** `CapWords` (e.g., `OptionalCallableOrStr`)
*   **Functions and Methods:** `lowercase_with_underscores()` (e.g., `merge_record_extra()`)
*   **Variables:** `lowercase_with_underscores`
*   **Constants:** `UPPERCASE_WITH_UNDERSCORES` (e.g., `RESERVED_ATTRS`)

## Type Hinting

*   All new code **must** include type hints for function arguments, return types, and variables where appropriate.
*   Use standard types from the `typing` module (e.g., `Optional`, `Union`, `List`, `Dict`, `Callable`, `Any`).
*   For Python versions older than 3.10, use `typing_extensions.TypeAlias` for creating type aliases. For Python 3.10+, use `typing.TypeAlias`.

## Docstrings

*   All public modules, classes, functions, and methods **must** have docstrings.
*   We use `mkdocstrings` for generating API documentation, which defaults to the **Google Python Style Guide** for docstrings. Please adhere to this style. You can find the guide [here](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
*   Docstrings should clearly explain the purpose, arguments, return values, and any exceptions raised.
*   Use the following markers to indicate changes over time:
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
        if param2 < 0:
            raise ValueError("param2 cannot be negative")
        # ... function logic ...
        return True
    ```

## Return Statements

*   **All functions and methods must have an explicit `return` statement.**
*   If a function does not logically return a value, it should end with `return None` or simply `return`. This makes the intent clear.

    Example:
    ```python
    def process_data(data: dict) -> None:
        """Processes the given data."""
        # ... processing logic ...
        print(data)
        return # or return None
    ```

## Class Structure

*   Group methods logically within a class. For example:
    *   Initialization methods (`__init__`, `__new__`)
    *   Public methods
    *   Protected/Private methods (by convention, prefixed with `_` or `__`)
    *   Special methods (`__str__`, `__repr__`)
*   Within source code comments, use `## Section Name ##` or `### Subsection Name ###` to delineate logical sections if it improves readability, especially in larger classes (e.g., `## Parent Methods ##` as seen in `src/pythonjsonlogger/core.py`).

## Testing

This project uses `pytest` for testing.

*   **Test Location:** Tests are located in the `tests/` directory.
*   **Test Naming:** Test files should be named `test_*.py` and test functions/methods should be prefixed with `test_`.
*   **Fixtures:** Utilize `pytest` fixtures (e.g., `@pytest.fixture`) for setting up test preconditions and managing test state.
    *   The `LoggingEnvironment` dataclass and `env` fixture in `tests/test_formatters.py` are good examples of reusable test setups for logger testing. Strive to create similar helpers for common testing scenarios.
*   **Parametrization:** Use `@pytest.mark.parametrize` to run the same test function with different inputs and expected outputs. This is highly encouraged to reduce code duplication and cover multiple scenarios efficiently.
*   **Clarity and Focus:** Each test case should ideally test one specific aspect of functionality. Test names should be descriptive of what they are testing.
*   **Assertions:** Use clear and specific `pytest` assertions (e.g., `assert foo == bar`, `assert isinstance(obj, MyClass)`).
*   **Robustness:** Write tests that are not overly brittle. For example, avoid making assertions on exact string matches of complex, auto-generated outputs if only a part of it is relevant.

## Common Code Patterns and Idioms

*   **Version-Specific Logic:** When code needs to behave differently based on the Python version, use `sys.version_info`:
    ```python
    if sys.version_info >= (3, 10):
        # Python 3.10+ specific code
        pass
    else:
        # Code for older versions
        pass
    ```
*   **Type Aliases for Clarity:** Use `TypeAlias` for complex or frequently used type combinations to improve readability.
    ```python
    from typing import List, Tuple, Union
    from typing_extensions import TypeAlias # For Python < 3.10

    Coordinate: TypeAlias = Tuple[int, int]
    PointOrListOfPoints: TypeAlias = Union[Coordinate, List[Coordinate]]
    ```
*   **Custom Exceptions:** Define custom exception classes for application-specific error conditions to provide more meaningful error information (e.g., `MissingPackageError`).
*   **Helper/Utility Functions:** Encapsulate reusable logic into well-named helper functions, often placed in `utils.py` or similar utility modules.

## Comments

*   Use comments to explain non-obvious code, complex logic, or important decisions.
*   Avoid comments that merely restate what the code does.
*   Module-level, class-level, and function/method-level explanations should primarily be in docstrings.
*   For internal code organization within files, especially in longer modules or classes, use comments like `## Section Title ##` or `### Subsection Title ###` to delineate logical blocks of code. This is distinct from Markdown headings used in this document.

By following these guidelines, we can ensure that `python-json-logger` remains a high-quality, maintainable, and developer-friendly library.
