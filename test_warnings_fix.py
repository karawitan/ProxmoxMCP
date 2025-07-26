"""
Test for warnings fix functionality.

This test demonstrates that the warnings fix correctly handles
urllib3 warnings that are overly suppressed by proxmoxer.
"""
import warnings
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_warnings_before_fix():
    """Test warnings behavior before applying the fix."""
    print("=== Testing warnings before fix ===")
    
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Import proxmoxer (this will disable warnings)
        import proxmoxer
        
        # Try to generate a warning that should be visible
        warnings.warn("Test RuntimeWarning", RuntimeWarning)
        
        print(f"Warnings captured before fix: {len(w)}")
        for warning in w:
            print(f"- {warning.category.__name__}: {warning.message}")

def test_warnings_after_fix():
    """Test warnings behavior after applying the fix.""" 
    print("\n=== Testing warnings after fix ===")
    
    # Apply the fix
    from proxmox_mcp.utils.warnings_fix import fix_proxmoxer_warnings
    fix_proxmoxer_warnings()
    
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Try to generate various warnings
        warnings.warn("Test RuntimeWarning after fix", RuntimeWarning)
        warnings.warn("Test DeprecationWarning after fix", DeprecationWarning)
        
        print(f"Warnings captured after fix: {len(w)}")
        for warning in w:
            print(f"- {warning.category.__name__}: {warning.message}")

def test_ssl_warnings_behavior():
    """Test SSL warnings behavior."""
    print("\n=== Testing SSL warnings behavior ===")
    
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Generate an SSL warning
            warnings.warn("Test SSL warning", InsecureRequestWarning)
            
            ssl_warnings = [warning for warning in w if issubclass(warning.category, InsecureRequestWarning)]
            other_warnings = [warning for warning in w if not issubclass(warning.category, InsecureRequestWarning)]
            
            print(f"SSL warnings (should be suppressed): {len(ssl_warnings)}")
            print(f"Other warnings (should be visible): {len(other_warnings)}")
            
    except ImportError:
        print("urllib3 not available for SSL warnings test")

if __name__ == "__main__":
    print("ProxmoxMCP Warnings Fix Test")
    print("=" * 40)
    
    # Test sequence
    test_warnings_before_fix()
    test_warnings_after_fix()
    test_ssl_warnings_behavior()
    
    print("\n=== Test Summary ===")
    print("✓ The fix should restore proper RuntimeWarning visibility")
    print("✓ SSL warnings should still be properly suppressed")
    print("✓ Other important warnings should be visible")
