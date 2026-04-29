#!/usr/bin/env python
"""
Loglife Desktop Application - Entry Point

Desktop application for report management with Azure AD authentication.
"""

import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Import after loading environment
from src.app import main

if __name__ == '__main__':
    sys.exit(main())
