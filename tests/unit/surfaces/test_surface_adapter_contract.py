from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path
from typing import get_type_hints

from capability_runner.contracts.surfaces import ApplicationProfile, SurfaceSessionRef
from capability_runner.surfaces.surface_adapter import SurfaceAdapter


def test_surface_adapter_has_no_playwright_dependency() -> None:
    script = """
import importlib
import sys

importlib.import_module('capability_runner.surfaces.surface_adapter')
assert 'playwright' not in sys.modules
print('ok')
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ok" in completed.stdout


def test_surface_adapter_api_does_not_expose_raw_handles() -> None:
    hints = get_type_hints(SurfaceAdapter.open_surface_session)
    signature = inspect.signature(SurfaceAdapter.open_surface_session)

    assert hints["return"] is SurfaceSessionRef
    assert hints["profile"] is ApplicationProfile
    assert signature.parameters["profile"].annotation == "ApplicationProfile"
    assert set(SurfaceSessionRef.model_fields) == {"surface_session_id", "surface_kind"}


def test_runner_source_does_not_import_demo_app() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "capability_runner"
    for path in source_root.rglob("*.py"):
        assert "demo_app" not in path.read_text(encoding="utf-8")
