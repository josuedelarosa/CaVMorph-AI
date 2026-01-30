#!/usr/bin/env python3
"""
Test script for cavfish_backend package.
Verifies the backend can be imported and started.
"""

import sys
import subprocess
from pathlib import Path

def test_backend_import():
    """Test that backend package can be imported."""
    print("Testing backend import...")
    try:
        sys.path.insert(0, str(Path(__file__).parent / "backend"))
        import cavfish_backend
        print(f"✓ cavfish_backend version: {cavfish_backend.__version__}")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_backend_cli():
    """Test that backend CLI works."""
    print("\nTesting backend CLI...")
    try:
        result = subprocess.run(
            ["python3", "-m", "cavfish_backend", "--help"],
            cwd=Path(__file__).parent / "backend",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Backend CLI works")
            print("\nCLI Help Output:")
            print(result.stdout)
            return True
        else:
            print(f"✗ CLI failed with code {result.returncode}")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False

def test_bootstrap_script():
    """Test that bootstrap script exists and is valid."""
    print("\nTesting bootstrap script...")
    bootstrap_path = Path(__file__).parent / "desktop" / "bootstrap_backend.py"
    
    if not bootstrap_path.exists():
        print(f"✗ Bootstrap script not found at {bootstrap_path}")
        return False
    
    print(f"✓ Bootstrap script found at {bootstrap_path}")
    
    # Test help
    try:
        result = subprocess.run(
            ["python3", str(bootstrap_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Bootstrap script is executable")
            return True
        else:
            print(f"✗ Bootstrap script failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Bootstrap test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Self-Bootstrap Architecture")
    print("=" * 60)
    
    results = []
    
    results.append(("Backend Import", test_backend_import()))
    results.append(("Backend CLI", test_backend_cli()))
    results.append(("Bootstrap Script", test_bootstrap_script()))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✓ All tests passed! The backend is ready for deployment.")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
