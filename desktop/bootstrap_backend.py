#!/usr/bin/env python3
"""
Bootstrap script for MorphologIA Backend.
Creates venv, installs dependencies, downloads model weights.

This script is bundled with the Tauri app and run on first launch.
"""

import sys
import os
import json
import hashlib
import urllib.request
import subprocess
import platform
from pathlib import Path
from typing import Optional


class BootstrapConfig:
    """Configuration for bootstrap process."""
    
    def __init__(self, app_data_dir: Optional[Path] = None):
        if app_data_dir is None:
            # Default app data directory
            if platform.system() == "Darwin":
                app_data_dir = Path.home() / "Library" / "Application Support" / "FishMorph"
            elif platform.system() == "Windows":
                app_data_dir = Path(os.getenv("APPDATA", "")) / "FishMorph"
            else:  # Linux
                app_data_dir = Path.home() / ".local" / "share" / "FishMorph"
        
        self.app_data_dir = Path(app_data_dir)
        self.venv_dir = self.app_data_dir / "venv"
        self.models_dir = self.app_data_dir / "models"
        self.logs_dir = self.app_data_dir / "logs"
        self.backend_dir = self.app_data_dir / "backend"
        
        # Python requirements
        self.python_version = "3.10"
        
        # Model configuration
        self.model_url = "https://your-model-hosting-url/model_weights.pth"
        self.model_checksum = "YOUR_SHA256_CHECKSUM_HERE"
        self.model_filename = "model_weights.pth"
        
        # Config files
        self.config_json = self.app_data_dir / "config.json"
    
    def ensure_directories(self):
        """Create all required directories."""
        for directory in [self.app_data_dir, self.venv_dir, self.models_dir, 
                         self.logs_dir, self.backend_dir]:
            directory.mkdir(parents=True, exist_ok=True)


class BootstrapLogger:
    """Simple logger for bootstrap process."""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Write log message to file and stdout."""
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        print(log_line.strip())
        with open(self.log_file, "a") as f:
            f.write(log_line)
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def warning(self, message: str):
        self.log(message, "WARNING")


class BackendBootstrapper:
    """Manages backend environment setup."""
    
    def __init__(self, config: BootstrapConfig):
        self.config = config
        self.logger = BootstrapLogger(config.logs_dir / "bootstrap.log")
    
    def check_python(self) -> bool:
        """Check if suitable Python is available."""
        self.logger.info(f"Checking for Python {self.config.python_version}...")
        
        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            self.logger.info(f"Found Python: {version}")
            
            # Extract version number (e.g., "Python 3.9.6" -> (3, 9, 6))
            try:
                version_parts = version.split()[1].split('.')
                major, minor = int(version_parts[0]), int(version_parts[1])
                
                # Accept Python 3.9+ (compatible with 3.10 for our use case)
                if major == 3 and minor >= 9:
                    self.logger.info(f"Python version {major}.{minor} is compatible")
                    return True
                else:
                    self.logger.warning(f"Python version {major}.{minor} is too old. Required: 3.9+")
                    return False
            except (IndexError, ValueError) as e:
                self.logger.error(f"Could not parse Python version: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Python check failed: {e}")
            return False
    
    def create_venv(self) -> bool:
        """Create virtual environment."""
        self.logger.info(f"Creating virtual environment at {self.config.venv_dir}...")
        
        try:
            # Remove existing venv if present
            if self.config.venv_dir.exists():
                self.logger.info("Removing existing venv...")
                import shutil
                shutil.rmtree(self.config.venv_dir)
            
            # Create new venv
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.config.venv_dir)],
                check=True,
                capture_output=True
            )
            
            self.logger.info("Virtual environment created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create venv: {e}")
            return False
    
    def get_venv_python(self) -> Path:
        """Get path to Python executable in venv."""
        if platform.system() == "Windows":
            return self.config.venv_dir / "Scripts" / "python.exe"
        else:
            return self.config.venv_dir / "bin" / "python"
    
    def install_dependencies(self, backend_source_dir: Path) -> bool:
        """Install backend dependencies from pyproject.toml."""
        self.logger.info("Installing backend dependencies...")
        
        python_exe = self.get_venv_python()
        
        try:
            # Upgrade pip first
            self.logger.info("Upgrading pip...")
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                capture_output=True
            )
            
            # Install backend package in editable mode
            self.logger.info(f"Installing backend from {backend_source_dir}...")
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "-e", str(backend_source_dir)],
                check=True,
                capture_output=True,
                timeout=600  # 10 minute timeout
            )
            
            self.logger.info("Dependencies installed successfully")
            return True
        except subprocess.TimeoutExpired:
            self.logger.error("Installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def download_model(self) -> bool:
        """Download and verify model weights."""
        model_path = self.config.models_dir / self.config.model_filename
        
        # Skip if already exists and verified
        if model_path.exists():
            self.logger.info(f"Model file exists at {model_path}, verifying checksum...")
            if self.verify_checksum(model_path):
                self.logger.info("Model checksum verified, skipping download")
                return True
            else:
                self.logger.warning("Model checksum mismatch, re-downloading...")
                model_path.unlink()
        
        self.logger.info(f"Downloading model from {self.config.model_url}...")
        
        try:
            # Download with progress (simple version)
            urllib.request.urlretrieve(self.config.model_url, model_path)
            
            self.logger.info("Model downloaded, verifying checksum...")
            if self.verify_checksum(model_path):
                self.logger.info("Model verified successfully")
                return True
            else:
                self.logger.error("Model checksum verification failed")
                model_path.unlink()
                return False
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            return False
    
    def verify_checksum(self, file_path: Path) -> bool:
        """Verify file SHA256 checksum."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            file_checksum = sha256_hash.hexdigest()
            expected = self.config.model_checksum.lower()
            
            if file_checksum == expected:
                return True
            else:
                self.logger.error(f"Checksum mismatch: expected {expected}, got {file_checksum}")
                return False
        except Exception as e:
            self.logger.error(f"Checksum verification error: {e}")
            return False
    
    def copy_backend_source(self, source_dir: Path) -> bool:
        """Copy backend source code to app data directory."""
        self.logger.info(f"Copying backend source from {source_dir}...")
        
        try:
            import shutil
            
            # Remove existing backend if present
            if self.config.backend_dir.exists():
                shutil.rmtree(self.config.backend_dir)
            
            # Copy backend directory
            shutil.copytree(source_dir, self.config.backend_dir, 
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))
            
            self.logger.info("Backend source copied successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy backend source: {e}")
            return False
    
    def save_config(self):
        """Save bootstrap configuration."""
        config_data = {
            "backend_version": "0.1.0",
            "python_version": self.config.python_version,
            "venv_path": str(self.config.venv_dir),
            "models_path": str(self.config.models_dir),
            "backend_path": str(self.config.backend_dir),
            "bootstrapped": True
        }
        
        with open(self.config.config_json, "w") as f:
            json.dump(config_data, f, indent=2)
        
        self.logger.info(f"Configuration saved to {self.config.config_json}")
    
    def bootstrap(self, backend_source_dir: Path) -> bool:
        """Run full bootstrap process."""
        self.logger.info("=== Starting MorphologIA Backend Bootstrap ===")
        
        # Ensure directories exist
        self.config.ensure_directories()
        
        # Check Python
        if not self.check_python():
            self.logger.error("Python check failed")
            return False
        
        # Create venv
        if not self.create_venv():
            self.logger.error("Failed to create virtual environment")
            return False
        
        # Copy backend source
        if not self.copy_backend_source(backend_source_dir):
            self.logger.error("Failed to copy backend source")
            return False
        
        # Install dependencies
        if not self.install_dependencies(self.config.backend_dir):
            self.logger.error("Failed to install dependencies")
            return False
        
        # Download model (optional - can fail if URL not configured)
        if self.config.model_url and self.config.model_url != "https://your-model-hosting-url/model_weights.pth":
            if not self.download_model():
                self.logger.warning("Model download failed, but continuing...")
        else:
            self.logger.info("Model download skipped (no URL configured)")
        
        # Save config
        self.save_config()
        
        self.logger.info("=== Bootstrap completed successfully ===")
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bootstrap MorphologIA Backend")
    parser.add_argument("--backend-source", type=str, required=True,
                       help="Path to backend source directory")
    parser.add_argument("--app-data-dir", type=str, default=None,
                       help="Custom app data directory (optional)")
    
    args = parser.parse_args()
    
    # Create config
    config = BootstrapConfig(
        app_data_dir=Path(args.app_data_dir) if args.app_data_dir else None
    )
    
    # Run bootstrap
    bootstrapper = BackendBootstrapper(config)
    backend_source = Path(args.backend_source).resolve()
    
    if not backend_source.exists():
        print(f"ERROR: Backend source directory not found: {backend_source}")
        sys.exit(1)
    
    success = bootstrapper.bootstrap(backend_source)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
