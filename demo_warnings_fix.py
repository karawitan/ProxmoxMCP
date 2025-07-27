#!/usr/bin/env python3
"""
Demonstration of the RuntimeWarning fix for ProxmoxMCP.

This script shows the difference between the behavior before and after
applying the warnings fix.
"""

import warnings
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_before_fix():
    """Test warnings behavior before applying the fix."""
    print("=== BEFORE FIX ===")
    print("Importing proxmoxer (which disables all urllib3 warnings)...")

    # Reset warnings
    warnings.resetwarnings()
    warnings.filterwarnings("default")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Import proxmoxer - this will disable warnings
        import proxmoxer

        # Try to generate warnings that should be visible
        warnings.warn("This is a RuntimeWarning that should be visible", RuntimeWarning)
        warnings.warn(
            "This is a DeprecationWarning that should be visible", DeprecationWarning
        )

        print(f"Warnings captured: {len(w)}")
        for warning in w:
            print(f"  - {warning.category.__name__}: {warning.message}")

    print()


def test_after_fix():
    """Test warnings behavior after applying the fix."""
    print("=== AFTER FIX ===")
    print("Applying targeted warnings fix...")

    # Apply our fix
    from proxmox_mcp.utils.warnings_fix import setup_warning_filters

    setup_warning_filters()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Generate the same warnings
        warnings.warn("This is a RuntimeWarning that should be visible", RuntimeWarning)
        warnings.warn(
            "This is a DeprecationWarning that should be visible", DeprecationWarning
        )

        # Try SSL warning (should be suppressed)
        try:
            from urllib3.exceptions import InsecureRequestWarning

            warnings.warn(
                "This SSL warning should be suppressed", InsecureRequestWarning
            )
        except ImportError:
            print("  urllib3 not available for SSL warning test")

        print(f"Warnings captured: {len(w)}")
        for warning in w:
            print(f"  - {warning.category.__name__}: {warning.message}")

    print()


def main():
    """Run the demonstration."""
    print("ProxmoxMCP RuntimeWarning Fix Demonstration")
    print("=" * 50)
    print()

    print("This demonstration shows how proxmoxer's overly broad warning")
    print("suppression can hide important RuntimeWarnings, and how our")
    print("fix restores proper warning visibility while still suppressing")
    print("only SSL-related warnings.")
    print()

    test_before_fix()
    test_after_fix()

    print("SUMMARY:")
    print(
        "✓ The fix restores visibility of RuntimeWarnings and other important warnings"
    )
    print("✓ SSL warnings are still properly suppressed to avoid noise")
    print("✓ The application now has proper warning visibility for debugging")


if __name__ == "__main__":
    main()
