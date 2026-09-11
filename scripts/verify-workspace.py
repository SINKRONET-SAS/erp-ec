"""Ensaya el centro de trabajo en la copia operativa aislada."""
from pathlib import Path
import subprocess, sys
sys.exit(subprocess.call([sys.executable, str(Path(__file__).with_name('verify-fiscal-native.py')), '--workspace']))
