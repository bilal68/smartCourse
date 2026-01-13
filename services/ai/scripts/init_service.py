#!/usr/bin/env python3
"""Initialize AI service database and run migrations."""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f"Running: {command}")
    result = subprocess.run(
        command, 
        shell=True, 
        cwd=cwd,
        capture_output=True, 
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Error output: {result.stderr}")
        sys.exit(1)
    
    print(result.stdout)
    return result.stdout

def main():
    """Initialize the AI service."""
    ai_service_path = Path(__file__).parent.parent
    
    print("🚀 Initializing AI Service...")
    
    # 1. Create the database
    print("\n📊 Creating AI service database...")
    run_command("python scripts/create_db.py", cwd=ai_service_path)
    
    # 2. Run Alembic migration to create tables
    print("\n🏗️ Running database migrations...")
    run_command("alembic revision --autogenerate -m 'Initial AI service schema'", cwd=ai_service_path)
    run_command("alembic upgrade head", cwd=ai_service_path)
    
    print("\n✅ AI Service initialization complete!")
    print("\nNext steps:")
    print("1. Start the AI service: python -m uvicorn app.main:app --reload --port 8001")
    print("2. Test the API: http://localhost:8001/docs")
    print("3. Check health: http://localhost:8001/health")

if __name__ == "__main__":
    main()