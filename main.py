#!/usr/bin/env python3
"""
VitaeForge — entry point for direct execution.

Usage:
  python main.py --jd jobs/my_job.txt --lang en --theme harmony --model gpt-4o-mini
  python main.py --jd jobs/my_job.txt --lang en --auto
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from entrypoints.cli import main

if __name__ == "__main__":
    main()
