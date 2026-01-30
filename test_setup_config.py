#!/usr/bin/env python3
"""
Test script to validate setup_first_run.py configuration
Does NOT run the actual installation, just validates the script can load and has correct structure.
"""

import sys
from pathlib import Path

# Add desktop directory to path
desktop_dir = Path(__file__).parent / "desktop"
sys.path.insert(0, str(desktop_dir))

def test_import():
    """Test that the setup script can be imported."""
    print("✓ Testing import...")
    try:
        import setup_first_run
        print("  ✓ setup_first_run imported successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to import: {e}")
        return False

def test_configuration():
    """Test that configuration is correct."""
    print("\n✓ Testing configuration...")
    import setup_first_run
    
    checks = []
    
    # Check environment name
    if setup_first_run.ENV_NAME == "cavfish310":
        print(f"  ✓ ENV_NAME: {setup_first_run.ENV_NAME}")
        checks.append(True)
    else:
        print(f"  ✗ ENV_NAME incorrect: {setup_first_run.ENV_NAME}")
        checks.append(False)
    
    # Check Python version
    if setup_first_run.PYTHON_VERSION == "3.10":
        print(f"  ✓ PYTHON_VERSION: {setup_first_run.PYTHON_VERSION}")
        checks.append(True)
    else:
        print(f"  ✗ PYTHON_VERSION incorrect: {setup_first_run.PYTHON_VERSION}")
        checks.append(False)
    
    return all(checks)

def test_functions():
    """Test that all required functions exist."""
    print("\n✓ Testing functions...")
    import setup_first_run
    
    required_functions = [
        'find_conda',
        'run_command',
        'check_env_exists',
        'verify_packages',
        'step_check_system',
        'step_create_env',
        'step_install_pytorch',
        'step_install_mm_packages',
        'step_install_dependencies',
        'step_download_model',
        'step_finalize',
    ]
    
    checks = []
    for func_name in required_functions:
        if hasattr(setup_first_run, func_name):
            print(f"  ✓ {func_name}() exists")
            checks.append(True)
        else:
            print(f"  ✗ {func_name}() missing")
            checks.append(False)
    
    return all(checks)

def test_installation_sequence():
    """Test that the installation sequence functions are correctly structured."""
    print("\n✓ Testing installation sequence structure...")
    import setup_first_run
    import inspect
    
    checks = []
    
    # Check step_install_pytorch
    pytorch_source = inspect.getsource(setup_first_run.step_install_pytorch)
    
    # Should use python -m pip
    if '"-m", "pip"' in pytorch_source or "'-m', 'pip'" in pytorch_source:
        print("  ✓ step_install_pytorch uses 'python -m pip'")
        checks.append(True)
    else:
        print("  ✗ step_install_pytorch should use 'python -m pip'")
        checks.append(False)
    
    # Should install numpy via conda
    if "conda-forge" in pytorch_source and "numpy<2" in pytorch_source:
        print("  ✓ step_install_pytorch installs numpy<2 via conda-forge")
        checks.append(True)
    else:
        print("  ✗ step_install_pytorch should install numpy<2 via conda-forge")
        checks.append(False)
    
    # Check step_install_mm_packages
    mm_source = inspect.getsource(setup_first_run.step_install_mm_packages)
    
    # Should use python -m pip
    if '"-m", "pip"' in mm_source or "'-m', 'pip'" in mm_source:
        print("  ✓ step_install_mm_packages uses 'python -m pip'")
        checks.append(True)
    else:
        print("  ✗ step_install_mm_packages should use 'python -m pip'")
        checks.append(False)
    
    # Should install mmengine==0.10.7
    if "mmengine==0.10.7" in mm_source:
        print("  ✓ step_install_mm_packages installs mmengine==0.10.7")
        checks.append(True)
    else:
        print("  ✗ step_install_mm_packages should install mmengine==0.10.7")
        checks.append(False)
    
    # Should install mmcv==2.1.0
    if "mmcv==2.1.0" in mm_source:
        print("  ✓ step_install_mm_packages installs mmcv==2.1.0")
        checks.append(True)
    else:
        print("  ✗ step_install_mm_packages should install mmcv==2.1.0")
        checks.append(False)
    
    # Should clone mmpose from git
    if "github.com/open-mmlab/mmpose" in mm_source:
        print("  ✓ step_install_mm_packages clones mmpose from GitHub")
        checks.append(True)
    else:
        print("  ✗ step_install_mm_packages should clone mmpose from GitHub")
        checks.append(False)
    
    # Should install mmpose with -e
    if '"-e"' in mm_source or "'-e'" in mm_source:
        print("  ✓ step_install_mm_packages installs mmpose in editable mode")
        checks.append(True)
    else:
        print("  ✗ step_install_mm_packages should install mmpose with -e")
        checks.append(False)
    
    return all(checks)

def main():
    """Run all tests."""
    print("=" * 60)
    print("Setup Script Validation Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Import", test_import()))
    
    if results[0][1]:  # Only continue if import succeeded
        results.append(("Configuration", test_configuration()))
        results.append(("Functions", test_functions()))
        results.append(("Installation Sequence", test_installation_sequence()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("=" * 60)
    
    if all(result[1] for result in results):
        print("\n✓ All tests passed!")
        print("\nThe setup script is correctly configured with your installation sequence.")
        print("You can now build the app with: ./build.sh")
        return 0
    else:
        print("\n✗ Some tests failed!")
        print("\nPlease review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
