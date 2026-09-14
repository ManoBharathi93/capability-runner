from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "capability_runner"
EXPECTED_PACKAGES = {
    "application",
    "capabilities",
    "contracts",
    "discovery",
    "evidence",
    "interaction",
    "interfaces",
    "intervention",
    "replay",
    "surfaces",
}
VENDOR_ROOTS = {"anthropic", "gemma", "openai", "playwright"}
CAPABILITY_BUILDER_PATH = PACKAGE_ROOT / "capabilities" / "capability_builder.py"


def _module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_from_import(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""

    current_package = (
        _module_name(path) if path.name == "__init__.py" else _module_name(path).rpartition(".")[0]
    )
    package_parts = current_package.split(".") if current_package else []
    keep = max(0, len(package_parts) - (node.level - 1))
    resolved_parts = package_parts[:keep]
    if node.module:
        resolved_parts.extend(node.module.split("."))
    return ".".join(resolved_parts)


def _imports(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_import(path, node)
            if base:
                yield base
            if base == "capability_runner":
                yield from (f"{base}.{alias.name}" for alias in node.names)


def _relative(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def _top_level_subsystem(import_name: str) -> str | None:
    parts = import_name.split(".")
    if len(parts) >= 2 and parts[0] == "capability_runner":
        return parts[1]
    return None


def test_expected_subsystem_packages_exist() -> None:
    actual_packages = {
        path.parent.name
        for path in PACKAGE_ROOT.glob("*/__init__.py")
        if path.parent.name != "providers"
    }
    assert actual_packages == EXPECTED_PACKAGES
    assert (PACKAGE_ROOT / "discovery" / "providers" / "__init__.py").is_file()


def test_production_imports_follow_dependency_rules() -> None:
    violations: list[str] = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = _relative(path)
        subsystem = relative.partition("/")[0]

        for import_name in _imports(path):
            imported_subsystem = _top_level_subsystem(import_name)
            vendor_root = import_name.partition(".")[0]

            if subsystem == "contracts" and imported_subsystem not in {None, "contracts"}:
                violations.append(f"{relative}: contracts imports {import_name}")

            if subsystem == "contracts" and vendor_root in VENDOR_ROOTS:
                violations.append(f"{relative}: contracts imports vendor SDK {import_name}")

            if subsystem == "replay" and (
                imported_subsystem in {"discovery", "interfaces", "model_client"}
                or vendor_root in VENDOR_ROOTS
            ):
                violations.append(f"{relative}: replay imports {import_name}")

            if (
                relative == "surfaces/browser_surface_adapter.py"
                and imported_subsystem == "discovery"
            ):
                violations.append(f"{relative}: browser adapter imports model layer {import_name}")

            if relative in {
                "surfaces/browser_observation.py",
                "surfaces/browser_surface_adapter.py",
            } and (
                imported_subsystem == "application"
                or vendor_root in {"demo_app", "anthropic", "openai", "gemma"}
            ):
                violations.append(
                    f"{relative}: perception imports application/provider {import_name}"
                )

            if subsystem == "discovery" and import_name == (
                "capability_runner.surfaces.browser_surface_adapter"
            ):
                violations.append(f"{relative}: Discovery imports concrete browser adapter")

            if relative == "discovery/discovery_engine.py" and import_name.startswith(
                "capability_runner.discovery.providers"
            ):
                violations.append(
                    f"{relative}: Discovery Engine imports concrete provider {import_name}"
                )

            if path.name == "state_evaluator.py" and (
                imported_subsystem in {"discovery", "surfaces"} or vendor_root in VENDOR_ROOTS
            ):
                violations.append(f"{relative}: State Evaluator imports {import_name}")

            if vendor_root == "playwright" and relative != "surfaces/browser_surface_adapter.py":
                violations.append(f"{relative}: Playwright import is outside browser adapter")

            if (
                subsystem == "discovery"
                and "providers/" not in relative
                and vendor_root in VENDOR_ROOTS
            ):
                violations.append(f"{relative}: discovery core imports vendor SDK {import_name}")

            if vendor_root == "openai" and relative != "discovery/providers/openai_client.py":
                violations.append(f"{relative}: OpenAI SDK import is outside its adapter")

            if vendor_root == "anthropic" and relative != "discovery/providers/anthropic_client.py":
                violations.append(f"{relative}: Anthropic SDK import is outside its adapter")

            if subsystem == "evidence" and imported_subsystem in {
                "application",
                "discovery",
                "replay",
            }:
                violations.append(f"{relative}: evidence imports engine {import_name}")

            if vendor_root in {"demo_app", "tests"}:
                violations.append(f"{relative}: production imports {import_name}")

    assert violations == [], "\n".join(violations)


def test_execution_engines_do_not_dispatch_to_surfaces_directly() -> None:
    violations: list[str] = []
    engine_paths = (
        PACKAGE_ROOT / "discovery" / "discovery_engine.py",
        PACKAGE_ROOT / "replay" / "replay_engine.py",
    )
    for path in engine_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "perform_action":
                violations.append(f"{_relative(path)}: direct perform_action call")

    assert violations == [], "\n".join(violations)


def test_capability_builder_is_provider_browser_and_application_neutral() -> None:
    forbidden_imports = (
        "capability_runner.discovery",
        "capability_runner.interfaces.model_client",
        "capability_runner.surfaces.browser_surface_adapter",
        "anthropic",
        "gemma",
        "openai",
        "playwright",
    )
    imports = tuple(_imports(CAPABILITY_BUILDER_PATH))
    import_violations = [
        import_name
        for import_name in imports
        if any(
            import_name == forbidden or import_name.startswith(f"{forbidden}.")
            for forbidden in forbidden_imports
        )
    ]

    source = CAPABILITY_BUILDER_PATH.read_text(encoding="utf-8").casefold()
    application_literals = (
        "corebank",
        "member.search",
        "member.results",
        "member.account",
        "savings",
        "member_not_found",
    )
    literal_violations = [literal for literal in application_literals if literal in source]

    assert import_violations == []
    assert literal_violations == []


def test_intervention_is_engine_provider_and_concrete_browser_neutral() -> None:
    forbidden_imports = (
        "capability_runner.discovery",
        "capability_runner.interfaces.model_client",
        "capability_runner.replay",
        "capability_runner.surfaces.browser_surface_adapter",
        "anthropic",
        "gemma",
        "openai",
        "playwright",
    )
    violations: list[str] = []

    for path in (PACKAGE_ROOT / "intervention").glob("*.py"):
        for import_name in _imports(path):
            if any(
                import_name == forbidden or import_name.startswith(f"{forbidden}.")
                for forbidden in forbidden_imports
            ):
                violations.append(f"{_relative(path)}: intervention imports {import_name}")

    assert violations == [], "\n".join(violations)


def test_operator_console_does_not_bypass_core_or_import_engines() -> None:
    paths = (
        PACKAGE_ROOT / "application" / "operator_console.py",
        PACKAGE_ROOT / "interfaces" / "operator_http.py",
    )
    forbidden_imports = (
        "capability_runner.discovery",
        "capability_runner.interfaces.model_client",
        "capability_runner.replay",
        "capability_runner.surfaces.browser_surface_adapter",
        "anthropic",
        "gemma",
        "openai",
        "playwright",
    )
    violations: list[str] = []

    for path in paths:
        for import_name in _imports(path):
            if any(
                import_name == forbidden or import_name.startswith(f"{forbidden}.")
                for forbidden in forbidden_imports
            ):
                violations.append(f"{_relative(path)}: operator console imports {import_name}")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "perform_action":
                violations.append(f"{_relative(path)}: direct perform_action call")

    assert violations == [], "\n".join(violations)


def test_replay_continuation_is_model_free_and_does_not_dispatch_directly() -> None:
    path = PACKAGE_ROOT / "application" / "run_coordinator.py"
    forbidden_imports = (
        "capability_runner.discovery",
        "capability_runner.interfaces.model_client",
        "capability_runner.surfaces.browser_surface_adapter",
        "anthropic",
        "gemma",
        "openai",
        "playwright",
    )
    violations = [
        import_name
        for import_name in _imports(path)
        if any(
            import_name == forbidden or import_name.startswith(f"{forbidden}.")
            for forbidden in forbidden_imports
        )
    ]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if any(
        isinstance(node, ast.Attribute) and node.attr == "perform_action" for node in ast.walk(tree)
    ):
        violations.append("application/run_coordinator.py: direct perform_action call")

    assert violations == []


def test_package_initializers_contain_no_executable_statements() -> None:
    violations: list[str] = []
    allowed_nodes = (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)

    for path in PACKAGE_ROOT.rglob("__init__.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, allowed_nodes):
                violations.append(f"{_relative(path)}: disallowed {type(node).__name__}")
            elif isinstance(node, ast.Expr) and not (
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            ):
                violations.append(f"{_relative(path)}: executable expression")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if value is not None and not isinstance(value, ast.Constant):
                    violations.append(f"{_relative(path)}: non-constant assignment")

    assert violations == [], "\n".join(violations)


def test_generic_observation_discovery_and_compiler_have_no_demo_knowledge() -> None:
    paths = [
        PACKAGE_ROOT / name
        for name in (
            "discovery/discovery_engine.py",
            "discovery/browser_discovery.py",
            "capabilities/binding_compiler.py",
            "surfaces/browser_surface_adapter.py",
            "surfaces/browser_observation.py",
        )
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8").casefold()
        for forbidden in (
            "corebank",
            "legacybank",
            "demo_app",
            "lookup_savings_balance",
            "member.search",
            "member.results",
            "member.accounts",
            "savings",
        ):
            assert forbidden not in source, (path.name, forbidden)
        assert "perform_action" not in source or path.name == "browser_surface_adapter.py"
