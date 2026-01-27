#!/usr/bin/env python
"""Simple wrapper to run Temporal worker with debugpy."""

import asyncio
from app.workflows.worker import run_worker

if __name__ == "__main__":
    run_worker()
