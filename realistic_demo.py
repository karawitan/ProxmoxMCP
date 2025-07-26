#!/usr/bin/env python3
"""
Realistic demonstration of the RuntimeWarning fix for ProxmoxMCP.

This shows how the fix works in real usage scenarios.
"""

import warnings
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def demonstrate_real_usage():
    """Demonstrate the fix in a realistic usage scenario."""
    print("=== REAL USAGE DEMONSTRATION ===")
    print()
    
    # This is how the fix is applied in the actual application
    print("1. Setting up warning filters (as done in server.py)...")
    from proxmox_mcp.utils.warnings_fix import setup_warning_filters
    setup_warning_filters()
    
    print("2. Importing proxmox components...")
    # Import our proxmox module (which imports proxmoxer)
    try:
        import proxmox_mcp.core.proxmox
        print("   ✓ Proxmox core module imported")
    except Exception as e:
        print(f"   ✗ Error importing proxmox core: {e}")
    
    print("3. Testing warning visibility...")
    
    # Capture warnings normally (not with simplefilter)
    captured_warnings = []
    
    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append((category, str(message)))
    
    old_showwarning = warnings.showwarning
    warnings.showwarning = warning_handler
    
    try:
        # Generate test warnings
        warnings.warn("Test RuntimeWarning - should be visible", RuntimeWarning)
        warnings.warn("Test DeprecationWarning - should be visible", DeprecationWarning)
        
        # Try SSL warning (should be suppressed)
        try:
            from urllib3.exceptions import InsecureRequestWarning
            warnings.warn("Test SSL warning - should be suppressed", InsecureRequestWarning)
        except ImportError:
            pass
        
        print(f"   Warnings captured: {len(captured_warnings)}")
        for category, message in captured_warnings:
            print(f"   - {category.__name__}: {message}")
        
        # Check if we have the expected warnings
        runtime_warnings = [w for w in captured_warnings if w[0] == RuntimeWarning]
        ssl_warnings = [w for w in captured_warnings if 'InsecureRequestWarning' in str(w[0])]
        
        print()
        print("Results:")
        if runtime_warnings:
            print("   ✓ RuntimeWarnings are visible (good for debugging)")
        else:
            print("   ✗ RuntimeWarnings are not visible (could hide bugs)")
            
        if not ssl_warnings:
            print("   ✓ SSL warnings are suppressed (reduces noise)")
        else:
            print("   ⚠ SSL warnings are visible (might be noisy)")
            
    finally:
        warnings.showwarning = old_showwarning

def main():
    """Run the realistic demonstration."""
    print("ProxmoxMCP RuntimeWarning Fix - Real Usage Demo")
    print("=" * 50)
    print()
    
    print("This demonstrates how the fix works in the actual application")
    print("to ensure RuntimeWarnings remain visible for debugging while")
    print("SSL warnings are appropriately suppressed.")
    print()
    
    demonstrate_real_usage()
    
    print()
    print("CONCLUSION:")
    print("The fix ensures that important warnings like RuntimeWarning")
    print("remain visible for debugging, while only suppressing noisy")
    print("SSL certificate warnings from urllib3/requests.")

if __name__ == "__main__":
    main()
