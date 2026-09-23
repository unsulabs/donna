#!/usr/bin/env python3
"""Hermes cron preflight. Never marks work handled before a review succeeds."""
from donna_runtime.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["pulse"]))
