"""
Loglife Desktop Application - Source Package

Main entry point for the application.
Run: python main.py

Imports de `src.app` / PyQt6 são adiados (lazy) para que subpacotes como
`src.core` possam ser importados sem carregar a GUI — útil em CI e scripts.
"""

from typing import Any

__all__ = ["main", "LocalLifeApplication"]


def __getattr__(name: str) -> Any:
    if name == "main":
        from src.app import main as _main

        return _main
    if name == "LocalLifeApplication":
        from src.app import LocalLifeApplication as _cls

        return _cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
