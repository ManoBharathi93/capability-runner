"""Scripted evaluation fixture decisions; never used for live acceptance."""

import json
import re

from capability_runner.discovery.model_client import ModelRequest, ModelResponse


class BankingBrowserModel:
    def __init__(self, *, product: str = "savings", unsafe: bool = False) -> None:
        self.calls = 0
        self.product = product
        self.unsafe = unsafe

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        data = json.loads(request.messages[-1].content)
        if "observations" in data:
            return self._known(data)
        elements = data["elements"]
        decision: dict[str, object] = {"observation_id": data["observation_id"]}
        if self.unsafe:
            control = next(item for item in elements if "delete" in item["name"].lower())
            decision.update(kind="click", element_ref=control["ref"])
        elif any(item["label"] == "Available balance" for item in elements):
            identity = next(item for item in elements if item["label"] == "Customer reference")
            amount = next(item for item in elements if item["label"] == "Available balance")
            category = next(item for item in elements if item["label"] == "Product category")
            decision.update(
                kind="complete",
                evidence_refs=[identity["ref"], category["ref"], amount["ref"]],
                identity_refs={"input_1": identity["ref"]},
                outputs=[
                    {
                        "evidence_ref": amount["ref"],
                        "name": "balance_minor_units",
                        "parser": "currency_minor_units",
                    },
                    {"evidence_ref": amount["ref"], "name": "currency", "parser": "currency_code"},
                ],
            )
        else:
            fills = [item for item in elements if item["action_kind"] == "fill"]
            if fills and fills[0]["value_state"] == "empty":
                decision.update(kind="fill", element_ref=fills[0]["ref"], input_ref="input_1")
            else:
                controls = [item for item in elements if item["action_kind"] == "click"]
                control = next(
                    (item for item in controls if self.product in item["name"].lower()), controls[0]
                )
                decision.update(kind="click", element_ref=control["ref"])
        return ModelResponse(content=json.dumps(decision), provider="scripted", model="fixture")

    def _known(self, data):
        observations = {item["target"]: item for item in data["observations"]}
        targets = data["required_completion_targets"]
        if all(observations[target]["state"] == "VISIBLE" for target in targets):
            decision = {
                "kind": "COMPLETE",
                "evidence": [
                    {"target": target, "observed_text": observations[target]["text"]}
                    for target in targets
                ],
            }
        else:
            actions = [
                ("fill", "member.search.member_id"),
                ("click", "member.search.submit"),
                ("click", "member.results.open"),
                ("click", "member.accounts.savings"),
            ]
            index = len(data["action_history"])
            if index >= len(actions):
                decision = {"kind": "FAIL", "reason_code": "UNSUPPORTED_GOAL"}
            else:
                kind, target = actions[index]
                action = {"kind": kind, "target": target}
                if kind == "fill":
                    action["value"] = re.search(r"\d+", data["goal"]).group()
                decision = {"kind": "ACT", "action": action}
        return ModelResponse(content=json.dumps(decision), provider="scripted", model="fixture")
