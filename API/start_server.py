#!/usr/bin/env python3
"""
Simple startup script for DeepAnalyze API Server
"""
import sys
import os

# Fix encoding issues on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

if __name__ == "__main__":
    from main import main
    main()