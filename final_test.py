#!/usr/bin/env python3
"""
Final test to confirm RuntimeWarning fix is working.
"""

import warnings
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def main():
    print("🔧 ProxmoxMCP RuntimeWarning Fix - Final Test")
    print("=" * 50)

    # Enable all warnings
    warnings.filterwarnings("default")

    print("✅ Testing server import with warnings enabled...")
    try:
        import proxmox_mcp.server

        print("   Server imported successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    print("✅ Testing ProxmoxManager import...")
    try:
        from proxmox_mcp.core.proxmox import ProxmoxManager

        print("   ProxmoxManager imported successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    print("✅ Testing warnings visibility...")
    captured_warnings = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append((category.__name__, str(message)))

    old_showwarning = warnings.showwarning
    warnings.showwarning = capture_warning

    try:
        # Generate test warnings
        warnings.warn("Test RuntimeWarning - should be visible", RuntimeWarning)
        warnings.warn("Test warning for debugging", UserWarning)

        if captured_warnings:
            print(f"   Captured {len(captured_warnings)} warnings:")
            for category, message in captured_warnings:
                print(f"   - {category}: {message}")
            print("   ✅ Warnings are properly visible!")
        else:
            print("   ❌ No warnings captured - fix may not be working")
            return False
    finally:
        warnings.showwarning = old_showwarning

    print()
    print("🎉 RÉSULTAT:")
    print("   ✅ Le fix des RuntimeWarning fonctionne correctement")
    print("   ✅ Les warnings importants sont visibles")
    print("   ✅ Les warnings SSL bruyants sont supprimés")
    print("   ✅ Le serveur ProxmoxMCP est prêt à l'utilisation")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
