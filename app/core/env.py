import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_FILE = os.getenv("ENV_FILE")

if ENV_FILE:
    load_dotenv(BASE_DIR / ENV_FILE)
