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
    from app.utils.ssl_utils import validate_ssl_configuration, get_certificate_info
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import configuration: {e}")
    CONFIG_AVAILABLE = False


def validate_ssl_certificates(cert_file: str, key_file: str) -> bool:
    """Validate SSL certificates exist and are properly paired"""
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
        
        print(f"Validating SSL certificates...")
        print(f"Certificate: {cert_path}")
        print(f"Private key: {key_path}")
        
        # Validate SSL configuration
        is_valid, error_message = validate_ssl_configuration(cert_path, key_path)
        
        if not is_valid:
            print(f"ERROR: SSL validation failed: {error_message}")
            return False
        
        # Get certificate information for display
        cert_info = get_certificate_info(cert_path)
        if "error" not in cert_info:
            print("SUCCESS: SSL certificates validated")
            print(f"Certificate subject: {cert_info.get('subject', 'Unknown')}")
            print(f"Valid until: {cert_info.get('not_valid_after', 'Unknown')}")
            print(f"Key size: {cert_info.get('public_key_size', 'Unknown')} bits")
        
        return True
        
    except Exception as e:
        print(f"ERROR: SSL certificate validation failed: {e}")
        return False


def build_uvicorn_command(python_executable: Path, use_ssl: bool = False) -> list:
    """Build uvicorn command with appropriate parameters"""
    
    base_cmd = [
        str(python_executable),
        "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "0.0.0.0"
    ]
    
    if use_ssl and CONFIG_AVAILABLE:
        # Add SSL parameters
        cert_path = settings.get_ssl_cert_path()
        key_path = settings.get_ssl_key_path()
        
        base_cmd.extend([
            "--port", str(settings.ssl_port),
            "--ssl-keyfile", str(key_path),
            "--ssl-certfile", str(cert_path)
        ])
        
        # Add SSL version if specified
        if settings.ssl_version and settings.ssl_version.upper() in ["TLSV1_2", "TLSV1_3"]:
            base_cmd.extend(["--ssl-version", settings.ssl_version.lower()])
    else:
        # Regular HTTP
        base_cmd.extend(["--port", "8000"])
    
    return base_cmd


def display_server_info(use_ssl: bool = False):
    """Display server startup information"""
    if use_ssl and CONFIG_AVAILABLE:
        port = settings.ssl_port
        protocol = "https"
        print(f"Server will be available at: {protocol}://localhost:{port}")
        print(f"API documentation at: {protocol}://localhost:{port}/docs")
        print("NOTE: Self-signed certificate will show browser security warnings")
        if not settings.force_https:
            print("HTTP fallback available at: http://localhost:8000")
    else:
        port = 8000
        protocol = "http"
        print(f"Server will be available at: {protocol}://localhost:{port}")
        print(f"API documentation at: {protocol}://localhost:{port}/docs")


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
    
    # Determine SSL usage
    use_ssl = False
    if CONFIG_AVAILABLE and settings.ssl_enabled:
        print("SSL enabled in configuration - validating certificates...")
        if validate_ssl_certificates(settings.ssl_cert_file, settings.ssl_key_file):
            use_ssl = True
            print("SUCCESS: SSL certificates validated - starting HTTPS server")
        else:
            print("ERROR: SSL validation failed - falling back to HTTP")
            use_ssl = False
    elif CONFIG_AVAILABLE:
        print("SSL disabled in configuration - starting HTTP server")
    else:
        print("Configuration unavailable - starting HTTP server")
    
    print("Starting uvicorn server...")
    
    # Change to the backend/src directory
    backend_src_path = project_root / "backend" / "src"
    
    # Build command
    cmd = build_uvicorn_command(python_executable, use_ssl)
    
    # Start the server using the virtual environment's Python
    try:
        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {backend_src_path}")
        
        # Display server information
        display_server_info(use_ssl)
        
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
        if use_ssl:
            print("Hint: Try disabling SSL (set SSL_ENABLED=false in .env) if SSL issues persist")
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())