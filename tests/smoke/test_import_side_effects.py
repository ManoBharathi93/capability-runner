from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PACKAGE_NAMES = (
    "capability_runner",
    "capability_runner.application",
    "capability_runner.capabilities",
    "capability_runner.contracts",
    "capability_runner.discovery",
    "capability_runner.discovery.providers",
    "capability_runner.evidence",
    "capability_runner.interaction",
    "capability_runner.interfaces",
    "capability_runner.intervention",
    "capability_runner.replay",
    "capability_runner.surfaces",
)


def test_importing_packages_does_not_create_runtime_state(tmp_path: Path) -> None:
    script = """
import importlib
import json
import os
import pathlib
import sys

package_names = json.loads(sys.argv[1])
environment_before = dict(os.environ)
for package_name in package_names:
    importlib.import_module(package_name)

forbidden_roots = {"anthropic", "openai", "playwright"}
loaded_forbidden = sorted(
    name for name in sys.modules if name.partition(".")[0] in forbidden_roots
)
created_paths = sorted(
    str(path.relative_to(pathlib.Path.cwd())) for path in pathlib.Path.cwd().rglob("*")
)

assert os.environ == environment_before
assert loaded_forbidden == []
assert created_paths == []
print(json.dumps({"loaded_forbidden": loaded_forbidden, "created_paths": created_paths}))
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, json.dumps(PACKAGE_NAMES)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {"created_paths": [], "loaded_forbidden": []}