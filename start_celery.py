#!/usr/bin/env python3
"""
Script to start Celery worker for processing Reddit data fetching tasks.
"""

import subprocess
import sys
import os

def start_celery_worker():
    """Start Celery worker with appropriate configuration."""
    
    # Change to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Celery worker command
    cmd = [
        "celery",
        "-A", "src.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",  # Limit concurrent tasks to avoid overwhelming the system
        "--prefetch-multiplier=1"  # Process one task at a time per worker
    ]
    
    print("Starting Celery worker...")
    print(f"Command: {' '.join(cmd)}")
    print("Press Ctrl+C to stop the worker")
    print("-" * 50)
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nCelery worker stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Error starting Celery worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_celery_worker() 