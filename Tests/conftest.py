# Tests/conftest.py
import sys
from pathlib import Path

# Get the absolute path of the project root (two levels up from this file)
project_root = Path(__file__).parent.parent
# Add it to the front of sys.path so imports work no matter where pytest runs from
sys.path.insert(0, str(project_root))
