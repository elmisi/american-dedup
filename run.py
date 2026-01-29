#!/usr/bin/env python3
"""Entry point for american-dedup."""

import sys
from pathlib import Path

# Add current directory to path for development
sys.path.insert(0, str(Path(__file__).parent))

from american_dedup.app import main

if __name__ == "__main__":
    start_path = sys.argv[1] if len(sys.argv) > 1 else "/"
    main(start_path)
