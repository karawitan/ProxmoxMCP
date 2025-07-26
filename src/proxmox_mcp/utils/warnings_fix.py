"""
Fix for proxmoxer urllib3 warnings suppression.

This module provides a more targeted approach to suppress only SSL-related warnings
instead of all urllib3 warnings, which can hide important RuntimeWarnings.
"""

import warnings
import logging

try:
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning
    URLLIB3_AVAILABLE = True
except ImportError:
    URLLIB3_AVAILABLE = False
    
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def configure_ssl_warnings(suppress_ssl_warnings: bool = True):
    """
    Configure SSL warnings in a more targeted way.
    
    Args:
        suppress_ssl_warnings: If True, only suppress InsecureRequestWarning.
                              If False, enable all warnings.
    """
    if not URLLIB3_AVAILABLE:
        return
        
    if suppress_ssl_warnings:
        # Suppress SSL certificate warnings specifically
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
        # Alternative: use urllib3's disable_warnings for SSL warnings
        urllib3.disable_warnings(InsecureRequestWarning)
    else:
        # Re-enable SSL warnings
        warnings.filterwarnings("default", category=InsecureRequestWarning)


def restore_urllib3_warnings():
    """
    Restore all urllib3 warnings that were globally disabled by proxmoxer.
    
    This function should be called after importing proxmoxer to restore
    proper warning behavior.
    """
    if not URLLIB3_AVAILABLE:
        return
        
    # Reset warnings to default state
    warnings.resetwarnings()
    
    # Re-enable all warnings by default
    warnings.filterwarnings("default")
    
    # Set up urllib3 logging properly
    try:
        urllib3_logger = logging.getLogger('urllib3')
        if urllib3_logger.level == logging.NOTSET:
            urllib3_logger.setLevel(logging.WARNING)
    except Exception:
        pass
    
    # Only suppress SSL warnings specifically using both methods
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    urllib3.disable_warnings(InsecureRequestWarning)


def fix_proxmoxer_warnings():
    """
    Apply the fix for proxmoxer's overly broad warning suppression.
    
    This should be called after importing proxmoxer but before using it.
    The fix ensures that:
    1. RuntimeWarnings and other important warnings are visible
    2. Only SSL certificate warnings are suppressed
    3. Other urllib3 warnings remain visible
    """
    if REQUESTS_AVAILABLE and URLLIB3_AVAILABLE:
        # Re-enable warnings that proxmoxer disabled
        restore_urllib3_warnings()
        
        # Log that we've applied the fix
        logger = logging.getLogger("proxmox-mcp.warnings")
        logger.debug("Applied targeted SSL warnings suppression fix for proxmoxer")


def setup_warning_filters():
    """
    Set up warning filters for the entire application.
    
    This provides a centralized place to configure warning behavior
    for the entire Proxmox MCP server.
    """
    # Enable all warnings by default
    warnings.filterwarnings("default")
    
    # Apply the proxmoxer fix
    fix_proxmoxer_warnings()
    
    # Set up specific filters for common warning categories
    # You can add more specific filters here as needed
    
    # Example: Show deprecation warnings from our own code
    warnings.filterwarnings("default", category=DeprecationWarning, module="proxmox_mcp.*")
    
    # Example: Show runtime warnings from our own code  
    warnings.filterwarnings("default", category=RuntimeWarning, module="proxmox_mcp.*")
