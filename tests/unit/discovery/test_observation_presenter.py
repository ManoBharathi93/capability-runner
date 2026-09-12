from __future__ import annotations

import json

from capability_runner.contracts.evaluation import EvaluationSnapshot, TargetObservation
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
)
from capability_runner.discovery.observation_presenter import (
    MAX_GOAL_TEXT,
    MAX_OBSERVATION_TEXT,
    MAX_PRESENTED_TARGETS,
    ObservationPresenter,
)


def test_presentation_is_sorted_bounded_and_contains_no_locator_data() -> None:
    target_names = tuple(f"area.target_{index:02d}" for index in range(30, -1, -1))
    profile = ApplicationProfile.model_validate(
        {
            "profile_id": "test",
            "application_family": "test",
            "variant": "test",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value=target),
                    locator_candidates=(
                        CssLocator(kind="css", selector=f"#private-selector-{index}"),
                    ),
                    description=f"Target {index}",
                )
                for index, target in enumerate(target_names)
            ],
        }
    )
    snapshot = EvaluationSnapshot(
        observed_targets=tuple(
            TargetObservation(
                target=SemanticTargetRef(value=target),
                state="VISIBLE",
                text="x" * (MAX_OBSERVATION_TEXT + 100),
            )
            for target in target_names
        )
    )

    request = ObservationPresenter().present(
        goal="g" * (MAX_GOAL_TEXT + 100),
        profile=profile,
        snapshot=snapshot,
        turn=1,
        trace=(),
        required_completion_targets=(
            SemanticTargetRef(value="area.target_01"),
            SemanticTargetRef(value="area.target_02"),
        ),
    )
    payload = json.loads(request.messages[1].content)

    assert payload["goal"] == "g" * MAX_GOAL_TEXT
    assert payload["observations_truncated"] is True
    assert len(payload["observations"]) == MAX_PRESENTED_TARGETS
    assert [item["target"] for item in payload["observations"]] == sorted(target_names)[
        :MAX_PRESENTED_TARGETS
    ]
    assert all(len(item["text"]) == MAX_OBSERVATION_TEXT for item in payload["observations"])
    assert payload["required_completion_targets"] == ["area.target_01", "area.target_02"]
    assert "private-selector" not in request.messages[1].content