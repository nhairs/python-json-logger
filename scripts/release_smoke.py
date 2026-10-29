"""Check the installed wheel with an isolated Python interpreter."""

import logging

from pythonjsonlogger.json import JsonFormatter


def main() -> None:
    """Format one record without importing from the source checkout."""
    record = logging.LogRecord("release", 20, "", 0, "smoke", (), None)
    if JsonFormatter().format(record) != '{"message": "smoke"}':
        raise ValueError("Installed wheel formatting smoke test failed")
    return None


if __name__ == "__main__":
    main()
