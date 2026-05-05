#!/usr/bin/env python
"""
Loglife Desktop Application - Entry Point

Desktop application for report management with Azure AD authentication.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# .env ao lado do main.py ou do .exe (não substitui variáveis já definidas no Windows)
load_dotenv(_runtime_root() / ".env", override=False)

# Import after loading environment
from src.app import main

if __name__ == '__main__':
    sys.exit(main())
