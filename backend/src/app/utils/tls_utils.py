import ssl
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
import cryptography.x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import hashlib

logger = logging.getLogger(__name__)

class TLSValidationError(Exception):
    """Exception raised for TLS validation errors"""
    pass

def validate_certificate_files(cert_path: Path, key_path: Path) -> Dict[str, Any]:
    """
    Comprehensive certificate validation
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        
    Returns:
        Dict containing validation results and details
    """
    validation_result = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "cert_info": None,
        "key_info": None,
        "pair_matched": False
    }
    
    try:
        # File existence check
        if not cert_path.exists():
            validation_result["errors"].append(f"Certificate file not found: {cert_path}")
        if not key_path.exists():
            validation_result["errors"].append(f"Private key file not found: {key_path}")
        
        if validation_result["errors"]:
            return validation_result
        
        # Permission check (readable)
        if not cert_path.is_file() or not cert_path.stat().st_size > 0:
            validation_result["errors"].append(f"Certificate file is not readable or empty: {cert_path}")
        if not key_path.is_file() or not key_path.stat().st_size > 0:
            validation_result["errors"].append(f"Private key file is not readable or empty: {key_path}")
            
        if validation_result["errors"]:
            return validation_result
        
        # Load and validate certificate
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            cert = cryptography.x509.load_pem_x509_certificate(cert_data)
            validation_result["cert_info"] = _extract_certificate_info(cert)
            
            # Check certificate expiration
            now = datetime.now(timezone.utc)
            if cert.not_valid_after_utc < now:
                validation_result["errors"].append(f"Certificate expired on {cert.not_valid_after_utc}")
            elif cert.not_valid_after_utc < now + timedelta(days=30):
                validation_result["warnings"].append(f"Certificate expires soon: {cert.not_valid_after_utc}")
                
        except Exception as e:
            validation_result["errors"].append(f"Invalid certificate format: {str(e)}")
            
        # Load and validate private key
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            private_key = serialization.load_pem_private_key(key_data, password=None)
            validation_result["key_info"] = _extract_key_info(private_key)
            
        except Exception as e:
            validation_result["errors"].append(f"Invalid private key format: {str(e)}")
            
        # Verify certificate/key pair matching
        if validation_result["cert_info"] and validation_result["key_info"]:
            validation_result["pair_matched"] = _verify_key_pair_match(cert, private_key)
            if not validation_result["pair_matched"]:
                validation_result["errors"].append("Certificate and private key do not match")
        
        # Set overall validation status
        validation_result["valid"] = len(validation_result["errors"]) == 0
        
    except Exception as e:
        validation_result["errors"].append(f"Validation error: {str(e)}")
        logger.error(f"TLS validation error: {str(e)}")
        
    return validation_result

def _extract_certificate_info(cert: cryptography.x509.Certificate) -> Dict[str, Any]:
    """Extract certificate information for display"""
    try:
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        
        return {
            "subject": subject,
            "issuer": issuer,
            "serial_number": str(cert.serial_number),
            "not_valid_before": cert.not_valid_before_utc,
            "not_valid_after": cert.not_valid_after_utc,
            "signature_algorithm": cert.signature_algorithm_oid._name,
            "public_key_size": cert.public_key().key_size if hasattr(cert.public_key(), 'key_size') else None,
            "public_key_type": type(cert.public_key()).__name__,
            "fingerprint": cert.fingerprint(hashes.SHA256()).hex()
        }
    except Exception as e:
        logger.error(f"Error extracting certificate info: {str(e)}")
        return {"error": str(e)}

def _extract_key_info(private_key) -> Dict[str, Any]:
    """Extract private key information"""
    try:
        key_info = {
            "key_type": type(private_key).__name__,
        }
        
        if hasattr(private_key, 'key_size'):
            key_info["key_size"] = private_key.key_size
            
        return key_info
    except Exception as e:
        logger.error(f"Error extracting key info: {str(e)}")
        return {"error": str(e)}

def _verify_key_pair_match(cert: cryptography.x509.Certificate, private_key) -> bool:
    """Verify that certificate and private key match"""
    try:
        # Get public key from certificate
        cert_public_key = cert.public_key()
        
        # Get public key from private key
        if hasattr(private_key, 'public_key'):
            key_public_key = private_key.public_key()
        else:
            return False
            
        # Compare public key numbers for RSA keys
        if hasattr(cert_public_key, 'public_numbers') and hasattr(key_public_key, 'public_numbers'):
            return (cert_public_key.public_numbers().n == key_public_key.public_numbers().n and
                   cert_public_key.public_numbers().e == key_public_key.public_numbers().e)
        
        # For other key types, serialize and compare
        cert_public_pem = cert_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key_public_pem = key_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return cert_public_pem == key_public_pem
        
    except Exception as e:
        logger.error(f"Error verifying key pair match: {str(e)}")
        return False

def get_certificate_info(cert_path: Path) -> Dict[str, Any]:
    """
    Extract certificate information for display
    
    Args:
        cert_path: Path to certificate file
        
    Returns:
        Dict containing certificate information
    """
    try:
        if not cert_path.exists():
            return {"error": f"Certificate file not found: {cert_path}"}
            
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            
        cert = cryptography.x509.load_pem_x509_certificate(cert_data)
        return _extract_certificate_info(cert)
        
    except Exception as e:
        logger.error(f"Error reading certificate info: {str(e)}")
        return {"error": str(e)}

def create_tls_context(cert_file: Path, key_file: Path, tls_version: str = "TLS") -> ssl.SSLContext:
    """
    Create TLS context with security best practices
    
    Args:
        cert_file: Path to certificate file
        key_file: Path to private key file
        tls_version: TLS version to use
        
    Returns:
        Configured TLS context
        
    Raises:
        TLSValidationError: If certificate validation fails
    """
    # Validate certificates first
    validation_result = validate_certificate_files(cert_file, key_file)
    if not validation_result["valid"]:
        error_msg = "; ".join(validation_result["errors"])
        raise TLSValidationError(f"Certificate validation failed: {error_msg}")
    
    try:
        # Create TLS context with appropriate protocol
        if tls_version.upper() == "TLSV1_3":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_3
        elif tls_version.upper() == "TLSV1_2":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        else:
            # Default to TLS with secure minimum version
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Load certificate and private key
        context.load_cert_chain(str(cert_file), str(key_file))
        
        # Set security options
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        # Disable compression to prevent CRIME attacks
        context.options |= ssl.OP_NO_COMPRESSION
        
        # Disable renegotiation
        context.options |= getattr(ssl, 'OP_NO_RENEGOTIATION', 0)
        
        # Enable single DH use and single ECDH use
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        
        logger.info(f"TLS context created successfully with {tls_version}")
        return context
        
    except Exception as e:
        logger.error(f"Error creating TLS context: {str(e)}")
        raise TLSValidationError(f"Failed to create TLS context: {str(e)}")

def check_certificate_expiration(cert_path: Path, warning_days: int = 30) -> Dict[str, Any]:
    """
    Check certificate expiration and return status
    
    Args:
        cert_path: Path to certificate file
        warning_days: Days before expiration to show warning
        
    Returns:
        Dict containing expiration status
    """
    try:
        cert_info = get_certificate_info(cert_path)
        if "error" in cert_info:
            return {"status": "error", "message": cert_info["error"]}
            
        expiry_date = cert_info["not_valid_after"]
        now = datetime.utcnow()
        days_until_expiry = (expiry_date - now).days
        
        if days_until_expiry < 0:
            return {
                "status": "expired",
                "message": f"Certificate expired {abs(days_until_expiry)} days ago",
                "expiry_date": expiry_date,
                "days_until_expiry": days_until_expiry
            }
        elif days_until_expiry <= warning_days:
            return {
                "status": "warning", 
                "message": f"Certificate expires in {days_until_expiry} days",
                "expiry_date": expiry_date,
                "days_until_expiry": days_until_expiry
            }
        else:
            return {
                "status": "valid",
                "message": f"Certificate valid for {days_until_expiry} days",
                "expiry_date": expiry_date,
                "days_until_expiry": days_until_expiry
            }
            
    except Exception as e:
        logger.error(f"Error checking certificate expiration: {str(e)}")
        return {"status": "error", "message": str(e)}

def validate_tls_configuration(cert_path: Path, key_path: Path) -> Tuple[bool, str]:
    """
    Quick TLS configuration validation for startup checks
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        validation_result = validate_certificate_files(cert_path, key_path)
        
        if validation_result["valid"]:
            warnings = validation_result.get("warnings", [])
            if warnings:
                warning_msg = "; ".join(warnings)
                logger.warning(f"TLS configuration warnings: {warning_msg}")
            return True, "TLS configuration valid"
        else:
            error_msg = "; ".join(validation_result["errors"])
            return False, error_msg
            
    except Exception as e:
        return False, str(e)