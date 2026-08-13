"""Puts backend/ on sys.path before any test module is collected, so `import
app...` resolves regardless of a given test file's own import order -- the
same fixup run_eval.py does for itself at runtime, needed here too since
pytest may import a test module's `app.*` imports before that module's own
`import run_eval` line runs.
"""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
