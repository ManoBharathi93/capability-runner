from pathlib import Path

import pytest

from demo_app.evaluation import load_suite


def test_normal_suite_declares_real_workflows_and_profile_provenance() -> None:
    suite = load_suite(Path("evals/banking.yaml"), live=False)
    assert len(suite.cases) == 13
    assert len({case.goal for case in suite.cases}) >= 7
    assert any(case.product == "checking" for case in suite.cases)
    assert all(not case.profile_preexisting for case in suite.cases if case.application == "bank-b")


def test_live_suite_cannot_run_without_explicit_live_opt_in() -> None:
    with pytest.raises(ValueError, match="require --live"):
        load_suite(Path("evals/banking-live.yaml"), live=False)
    with pytest.raises(ValueError, match="normal suites cannot"):
        load_suite(Path("evals/banking.yaml"), live=True)


def test_live_acceptance_includes_previously_unprofiled_second_application() -> None:
    suite = load_suite(Path("evals/banking-live.yaml"), live=True)
    assert len(suite.cases) == 2
    case = next(case for case in suite.cases if case.application == "bank-b")
    assert case.generated_profile_expected and not case.profile_preexisting
