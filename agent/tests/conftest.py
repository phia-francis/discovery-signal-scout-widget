"""Test configuration for Signal Scout agent package.

Ensures the local ``signal_scout`` package under ``agent/`` is importable
without requiring an editable install. This keeps the test environment
lightweight and avoids relying on network access for build dependencies.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
