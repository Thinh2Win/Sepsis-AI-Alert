#!/usr/bin/env python3
"""
FastAPI Server Startup Script
Automates the process of activating virtual environment and starting the server
Supports both HTTP and HTTPS modes with SSL certificate validation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Add backend/src to path to import settings
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

try:
    from app.core.config import settings
    from app.utils.tls_utils import validate_tls_configuration, get_certificate_info
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import configuration: {e}")
    CONFIG_AVAILABLE = False


def validate_tls_certificates(cert_file: str, key_file: str) -> bool:
    """Validate TLS certificates exist and are properly paired"""
    if not CONFIG_AVAILABLE:
        print("ERROR: Configuration not available for SSL validation")
        return False
    
    try:
        cert_path = Path(cert_file)
        key_path = Path(key_file)
        
        # Make paths absolute if they're relative
        if not cert_path.is_absolute():
            cert_path = Path(__file__).parent / cert_file
        if not key_path.is_absolute():
            key_path = Path(__file__).parent / key_file
        
        print("Validating TLS certificates...")
        
        # Validate TLS configuration
        is_valid, error_message = validate_tls_configuration(cert_path, key_path)
        
        if not is_valid:
            print(f"ERROR: TLS validation failed: {error_message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"ERROR: TLS certificate validation failed: {e}")
        return False


def build_uvicorn_command(python_executable: Path) -> list:
    """Build uvicorn command for HTTPS server"""
    
    if not CONFIG_AVAILABLE:
        raise RuntimeError("Configuration not available - cannot start HTTPS server")
    
    cert_path = settings.get_tls_cert_path()
    key_path = settings.get_tls_key_path()
    
    base_cmd = [
        str(python_executable),
        "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", str(settings.tls_port),
        "--ssl-keyfile", str(key_path),
        "--ssl-certfile", str(cert_path)
    ]
    
    # Add TLS version if specified
    if settings.tls_version and settings.tls_version.upper() in ["TLSV1_2", "TLSV1_3"]:
        base_cmd.extend(["--ssl-version", settings.tls_version.lower()])
    
    return base_cmd


def display_server_info():
    """Display HTTPS server startup information"""
    if not CONFIG_AVAILABLE:
        print("ERROR: Configuration not available")
        return
    
    port = settings.tls_port
    print(f"Server will be available at: https://localhost:{port}")
    print(f"API documentation at: https://localhost:{port}/api/docs")
    print("NOTE: Self-signed certificate will show browser security warnings")
    print("INFO: HTTPS enforced for Auth0 JWT token security")


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
    
    # Validate TLS configuration
    if not CONFIG_AVAILABLE:
        print("ERROR: Configuration not available - cannot start HTTPS server")
        return 1
    
    if not settings.tls_enabled:
        print("ERROR: TLS is disabled - HTTPS server requires TLS_ENABLED=true")
        return 1
    
    print("TLS enabled in configuration - validating certificates...")
    if not validate_tls_certificates(settings.tls_cert_file, settings.tls_key_file):
        print("ERROR: TLS validation failed - cannot start HTTPS server")
        print("Please ensure valid TLS certificates are configured")
        return 1
    
    print("SUCCESS: TLS certificates validated - starting HTTPS server")
    
    print("Starting uvicorn server...")
    
    # Change to the backend/src directory
    backend_src_path = project_root / "backend" / "src"
    
    # Build command
    cmd = build_uvicorn_command(python_executable)
    
    # Start the server using the virtual environment's Python
    try:
        # Display server information
        display_server_info()
        
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
        print(f"ERROR: Error starting HTTPS server: {e}")
        print("Check TLS certificate configuration if server fails to start")
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())