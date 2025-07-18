#!/usr/bin/env python3
"""
FastAPI Server Startup Script
Automates the process of activating virtual environment and starting the server
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def main():
    """Main function to start the FastAPI server"""
    print("Starting Sepsis AI Alert FastAPI Server...")
    
    # Get the project root directory
    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")
    
    # Check if virtual environment exists
    venv_path = project_root / "venv"
    if not venv_path.exists():
        print("ERROR: Virtual environment not found at 'venv' directory")
        print("Please create virtual environment first: python -m venv venv")
        return 1
    
    # Determine the correct activation script based on OS
    if platform.system() == "Windows":
        python_executable = venv_path / "Scripts" / "python.exe"
        activate_script = venv_path / "Scripts" / "activate.bat"
    else:
        python_executable = venv_path / "bin" / "python"
        activate_script = venv_path / "bin" / "activate"
    
    # Check if Python executable exists in venv
    if not python_executable.exists():
        print(f"ERROR: Python executable not found at {python_executable}")
        print("Virtual environment may be corrupted. Please recreate it.")
        return 1
    
    # Check if main.py exists in backend/src
    main_py_path = project_root / "backend" / "src" / "main.py"
    if not main_py_path.exists():
        print(f"ERROR: main.py not found at {main_py_path}")
        print("Please ensure the FastAPI application exists in backend/src/main.py")
        return 1
    
    print("SUCCESS: Virtual environment found")
    print("SUCCESS: FastAPI application found")
    print("Starting uvicorn server...")
    
    # Change to the backend/src directory
    backend_src_path = project_root / "backend" / "src"
    
    # Start the server using the virtual environment's Python
    try:
        # Run uvicorn with the virtual environment's Python
        cmd = [
            str(python_executable),
            "-m", "uvicorn",
            "main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {backend_src_path}")
        print("Server will be available at: http://localhost:8000")
        print("API documentation at: http://localhost:8000/docs")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Run the command from the backend/src directory
        result = subprocess.run(
            cmd,
            cwd=backend_src_path,
            check=True
        )
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Error starting server: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())