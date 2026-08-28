import sys
from pathlib import Path

_root = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(_root / "shared"))
