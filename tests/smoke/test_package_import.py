from __future__ import annotations

import capability_runner


def test_package_import_exposes_version() -> None:
    assert capability_runner.__version__ == "0.1.0"