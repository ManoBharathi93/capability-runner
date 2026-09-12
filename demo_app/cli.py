"""Stable command-line entry point for reviewer demo flows."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from capability_runner.discovery.configuration import ModelConfigurationError

from .reviewer_runtime import (
    DEFAULT_OUTPUT_ROOT,
    DemoRunError,
    DemoRunResult,
    run_exception,
    run_intervention,
    run_through_line,
)

LIVE_CONFIGURATION_MESSAGE = (
    "Live model configuration is required for discovery demo. See .env.example."
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capability-runner",
        description="Run reproducible Capability Runner demonstrations.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    serve_parser = groups.add_parser("serve", help="Start the full local product.")
    serve_parser.add_argument("--port", type=int, default=5000)
    evaluation = groups.add_parser("eval", help="Evaluate Discovery and fresh model-free Replay.")
    evaluation_commands = evaluation.add_subparsers(dest="phase", required=True)
    for phase in ("discovery", "replay"):
        command = evaluation_commands.add_parser(phase)
        command.add_argument("--suite", type=Path, required=True)
        command.add_argument(
            "--live", action="store_true", help="Explicitly enable a real configured provider."
        )
    demo = groups.add_parser("demo", help="Run a reviewer demonstration.")
    commands = demo.add_subparsers(dest="demo_kind", required=True)

    through_line = commands.add_parser(
        "through-line",
        help="Discover, compile, store, and replay a capability.",
    )
    _add_output_root(through_line)
    intervention = commands.add_parser(
        "intervention",
        help="Demonstrate approval, operator action, and Replay continuation.",
    )
    _add_output_root(intervention)
    exception = commands.add_parser(
        "exception",
        help="Demonstrate a known model-free business outcome.",
    )
    _add_output_root(exception)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    arguments = create_parser().parse_args(argv)
    if arguments.group == "serve":
        from .product_http import main as serve

        serve(port=arguments.port)
        return 0
    if arguments.group == "eval":
        from .evaluation import evaluate

        try:
            path, report = evaluate(arguments.suite, live=arguments.live, phase=arguments.phase)
        except (ValueError, OSError):
            print("Invalid suite or live opt-in. See evals/README.md.", file=sys.stderr)
            return 2
        import json

        print(json.dumps(report["metrics"], indent=2))
        print(f"Report: {path.as_posix()}")
        metrics = report["metrics"]
        return 0 if metrics["passed"] == metrics["case_count"] else 1
    output_root = Path(arguments.output_root)
    try:
        if arguments.demo_kind == "through-line":
            result = run_through_line(
                environment=_load_environment() if environment is None else environment,
                output_root=output_root,
            )
        elif arguments.demo_kind == "intervention":
            result = run_intervention(output_root=output_root)
        else:
            result = run_exception(output_root=output_root)
    except ModelConfigurationError:
        print(LIVE_CONFIGURATION_MESSAGE, file=sys.stderr)
        return 2
    except DemoRunError as error:
        print(f"Demo verification failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Demo cancelled; runtime resources were closed.", file=sys.stderr)
        return 130
    except Exception:
        print(
            "Demo failed. Check provider configuration, Playwright Chromium, and local setup.",
            file=sys.stderr,
        )
        return 1

    _print_result(result)
    return 0


def _add_output_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Runtime output root (default: var/demo-runs).",
    )


def _load_environment(path: Path = Path(".env")) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    values.update(os.environ)
    return values


def _print_result(result: DemoRunResult) -> None:
    summary = result.summary
    demo_kind = summary["demo_kind"]
    if demo_kind == "through-line":
        print("Capability Runner - Discover -> Compile -> Replay")
        print("Discovery")
        print(f"  provider: {summary['provider']}")
        print("  goal: Find the savings balance for member [REDACTED].")
        print(f"  result: {summary['discovery_result']}")
        print(f"  model turns: {summary['discovery_model_calls']}")
        print("Compile")
        print(f"  capability: {summary['capability_id']}@{summary['capability_version']}")
        print(f"  stored: {summary['artifact_file']}")
        print(f"  model calls: {summary['builder_model_calls']}")
        print("Fresh replay")
        print("  input member_id: [REDACTED]")
        print(f"  result: {summary['replay_result']}")
        print(f"  balance_minor_units: {summary['balance_minor_units']}")
        print(f"  currency: {summary['currency']}")
        print(f"  model calls: {summary['replay_model_calls']}")
        print(f"Discovery model calls: {summary['discovery_model_calls']}")
        print(f"Builder model calls: {summary['builder_model_calls']}")
        print(f"Replay model calls: {summary['replay_model_calls']}")
    elif demo_kind == "intervention":
        print("Capability Runner - Approval -> Operator -> Resume")
        print("Automation suspended: APPROVAL_REQUIRED")
        print("Blocked action: Open Savings")
        print(f"Operator mode: {summary['operator_mode']}")
        print("Fresh state validation: PASS")
        print(f"Generation: {summary['generation_before']} -> {summary['generation_after']}")
        print(f"Result: {summary['replay_result']}")
        print(f"Balance: {summary['balance_minor_units']} {summary['currency']}")
    else:
        print("Capability Runner - Known Business Outcome")
        print(f"Classification: {summary['replay_result']}")
        print(f"Code: {summary['business_outcome']}")
        print("Replay model calls: 0")

    print(f"Run directory: {_portable_path(result.run_directory)}")
    print(f"Summary: {_portable_path(result.summary_path)}")
    print(f"Evidence: {summary['evidence_file']}")


def _portable_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.name


if __name__ == "__main__":
    raise SystemExit(main())
