import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_env() -> None:
    env_file = os.getenv("ENV_FILE")
    if not env_file:
        # prefer local file if available
        candidate = BASE_DIR / ".env.local"
        env_file = ".env.local" if candidate.exists() else ".env"
    load_dotenv(BASE_DIR / env_file, override=False)


# keep current behavior too (so importing this module auto-loads)
load_env()
