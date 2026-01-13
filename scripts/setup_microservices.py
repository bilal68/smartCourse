#!/usr/bin/env python3
"""Setup script for microservices architecture with separate databases."""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None, capture_output=True):
    """Run a command and return its output."""
    print(f"Running: {command}")
    result = subprocess.run(
        command, 
        shell=True, 
        cwd=cwd,
        capture_output=capture_output,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error running command: {command}")
        if result.stderr:
            print(f"Error output: {result.stderr}")
        if not capture_output:
            sys.exit(1)
    
    if capture_output and result.stdout:
        print(result.stdout)
    return result.stdout

def main():
    """Setup the microservices architecture."""
    root_path = Path(__file__).parent.parent
    lms_path = root_path / "services" / "lms"
    ai_path = root_path / "services" / "ai"
    
    print("🚀 Setting up SmartCourse Microservices Architecture...")
    
    # 1. Install dependencies for both services
    print("\n📦 Installing LMS service dependencies...")
    run_command("pip install httpx==0.25.2", cwd=lms_path, capture_output=False)
    
    print("\n📦 Installing AI service dependencies...")
    run_command("pip install -r requirements.txt", cwd=ai_path, capture_output=False)
    
    # 2. Create AI database
    print("\n📊 Creating AI service database...")
    try:
        run_command("python scripts/create_db.py", cwd=ai_path)
    except:
        print("Database creation may have failed - continuing...")
    
    # 3. Run AI service migrations
    print("\n🏗️ Setting up AI service database schema...")
    try:
        run_command("alembic revision --autogenerate -m 'Initial AI service schema'", cwd=ai_path)
        run_command("alembic upgrade head", cwd=ai_path)
    except:
        print("AI service migrations may have failed - check manually")
    
    print("\n✅ Microservices setup complete!")
    
    print("\n📋 Next Steps:")
    print("1. Update your .env.local file with:")
    print("   AI_SERVICE_URL=http://localhost:8001")
    
    print("\n2. Start both services:")
    print("   Terminal 1 (LMS):  cd services/lms && uvicorn app.main:app --reload --port 8000")
    print("   Terminal 2 (AI):   cd services/ai && uvicorn app.main:app --reload --port 8001")
    
    print("\n3. Test the new architecture:")
    print("   LMS API:  http://localhost:8000/docs")
    print("   AI API:   http://localhost:8001/docs")
    
    print("\n4. Content endpoints now available in LMS that proxy to AI:")
    print("   GET  /api/v1/content/courses/{id}/chunks")
    print("   POST /api/v1/content/search")
    print("   GET  /api/v1/content/courses/{id}/analysis")

if __name__ == "__main__":
    main()