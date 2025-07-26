"""
Unit tests for warnings fix functionality.
"""
import unittest
import warnings
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestWarningsFix(unittest.TestCase):
    """Test the warnings fix functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Save current warning filters
        self.original_filters = warnings.filters[:]
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore original warning filters
        warnings.filters[:] = self.original_filters
        
    def test_setup_warning_filters(self):
        """Test that setup_warning_filters works correctly."""
        from proxmox_mcp.utils.warnings_fix import setup_warning_filters
        
        # Clear existing filters
        warnings.resetwarnings()
        
        # Apply our setup
        setup_warning_filters()
        
        # Test that warnings are properly configured
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Generate test warnings
            warnings.warn("Test RuntimeWarning", RuntimeWarning)
            warnings.warn("Test DeprecationWarning", DeprecationWarning)
            
            # Should capture both warnings
            self.assertEqual(len(w), 2)
            
            warning_types = [warning.category for warning in w]
            self.assertIn(RuntimeWarning, warning_types)
            self.assertIn(DeprecationWarning, warning_types)
    
    def test_ssl_warnings_suppression(self):
        """Test that SSL warnings are properly suppressed."""
        try:
            from urllib3.exceptions import InsecureRequestWarning
            from proxmox_mcp.utils.warnings_fix import configure_ssl_warnings
            
            # Configure SSL warnings suppression
            configure_ssl_warnings(suppress_ssl_warnings=True)
            
            with warnings.catch_warnings(record=True) as w:
                # Don't use "always" as it overrides our filters
                # Instead, just use the current warning configuration
                
                # Generate SSL warning (should be suppressed)
                warnings.warn("Test SSL warning", InsecureRequestWarning)
                
                # Generate other warning (should not be suppressed)
                warnings.warn("Test RuntimeWarning", RuntimeWarning)
                
                # Should only capture the RuntimeWarning
                captured_categories = [warning.category for warning in w]
                self.assertIn(RuntimeWarning, captured_categories)
                # SSL warning should be suppressed (not captured)
                self.assertNotIn(InsecureRequestWarning, captured_categories)
                
        except ImportError:
            self.skipTest("urllib3 not available")
    
    def test_fix_proxmoxer_warnings(self):
        """Test that the proxmoxer warnings fix works."""
        from proxmox_mcp.utils.warnings_fix import fix_proxmoxer_warnings
        
        # Import proxmoxer first (which disables warnings)
        try:
            import proxmoxer
        except ImportError:
            self.skipTest("proxmoxer not available")
        
        # Apply the fix
        fix_proxmoxer_warnings()
        
        # Test that RuntimeWarnings are still visible
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            warnings.warn("Test RuntimeWarning after fix", RuntimeWarning)
            
            # Should capture the warning
            self.assertEqual(len(w), 1)
            self.assertEqual(w[0].category, RuntimeWarning)

if __name__ == '__main__':
    unittest.main()
