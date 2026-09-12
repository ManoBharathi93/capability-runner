"""Deterministic binding and capability compilation from verified browser facts."""

from __future__ import annotations

from collections.abc import Mapping

from capability_runner.contracts.browser_discovery import (
    BindingEvidence,
    BrowserDiscoveryResult,
    CapabilityPackage,
    InteractiveElement,
)
from capability_runner.contracts.capabilities import (
    ApplicationRequirement,
    CapabilityOutput,
    TargetTextSource,
)
from capability_runner.contracts.capability_building import (
    CapabilityBuildRequest,
    InputEqualitySuccessTemplate,
    InputSensitivityDeclaration,
    LiteralEqualitySuccessTemplate,
    SuccessTemplate,
    VisibleSuccessTemplate,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    InputValueRef,
    LiteralValue,
    SemanticTargetRef,
)
from capability_runner.surfaces.browser_observation import fingerprint, safe_slug

from .capability_builder import CapabilityBuilder


def compile_binding(
    element: InteractiveElement,
    inputs: Mapping[str, str],
) -> BrowserTargetBinding:
    if element.binding is None or element.match_count != 1:
        raise ValueError("TARGET_AMBIGUOUS")
    binding = element.binding.model_copy(update={"observation_id": None, "ephemeral_ref": None})
    row = binding.row_scope
    if row and isinstance(row.row_match.value, LiteralValue):
        input_name = next(
            (key for key, value in inputs.items() if value == row.row_match.value.value), None
        )
        if input_name:
            row = row.model_copy(
                update={
                    "row_match": row.row_match.model_copy(
                        update={"value": InputValueRef(name=input_name)}
                    )
                }
            )
            binding = binding.model_copy(update={"row_scope": row})
    serialized = binding.model_dump_json()
    if any(value and value in serialized for value in inputs.values()):
        raise ValueError("BINDING_CONTAINS_RUNTIME_VALUE")
    target = SemanticTargetRef(
        value=(
            f"page.x{fingerprint(serialized)[:8]}."
            f"{safe_slug(element.label or element.accessible_name)}"
        )
    )
    return binding.model_copy(update={"semantic_target": target})


def compile_package(
    discovery: BrowserDiscoveryResult,
    *,
    entry_point: str,
    capability_id: str,
    runtime_values: Mapping[str, str],
) -> CapabilityPackage:
    result = discovery.result
    completion = discovery.completion
    if result.outcome != "SUCCESS" or completion is None or discovery.identity is None:
        raise ValueError("DISCOVERY_NOT_SUCCESSFUL")
    bindings = tuple(compile_binding(item, runtime_values) for item in discovery.observed_bindings)
    by_ref = {
        item.ephemeral_ref: binding
        for item, binding in zip(discovery.observed_bindings, bindings, strict=True)
    }
    by_target = {item.semantic_target.value: item for item in bindings}
    evidence_by_ref = {item.ephemeral_ref: item for item in discovery.observed_bindings}
    success: list[SuccessTemplate] = []
    identity_refs = set(completion.identity_refs.values())
    for input_ref, ref in completion.identity_refs.items():
        success.append(
            InputEqualitySuccessTemplate(
                target=by_ref[ref].semantic_target,
                input_action_target=SemanticTargetRef(value=discovery.input_targets[input_ref]),
            )
        )
    output_refs = {item.evidence_ref for item in completion.outputs}
    for ref in completion.evidence_refs:
        if ref in identity_refs:
            continue
        target = by_ref[ref].semantic_target
        # Context facts (e.g. a selected record kind) become exact deterministic checkpoints.
        text = evidence_by_ref[ref].text
        if ref not in output_refs and text in discovery.verified_context and len(text) <= 160:
            success.append(LiteralEqualitySuccessTemplate(target=target, expected=text))
        else:
            success.append(VisibleSuccessTemplate(target=target))
    outputs = tuple(
        CapabilityOutput(
            name=item.name,
            value_type="INTEGER"
            if item.parser == "currency_minor_units"
            else "CURRENCY_CODE"
            if item.parser == "currency_code"
            else "STRING",
            source=TargetTextSource(
                target=by_ref[item.evidence_ref].semantic_target, parser=item.parser
            ),
        )
        for item in completion.outputs
    )
    family = "web_" + discovery.identity.fingerprint[:16]
    built = CapabilityBuilder().build(
        CapabilityBuildRequest(
            capability_id=capability_id,
            capability_version="1.0.0",
            name="Discovered " + " / ".join(item.name.replace("_", " ") for item in outputs)[:95],
            description="Observed browser workflow with grounded output and identity checkpoints.",
            discovery_result=result,
            application_requirement=ApplicationRequirement(
                application_family=family, surface_kind="browser"
            ),
            input_sensitivity=tuple(
                InputSensitivityDeclaration(
                    action_target=SemanticTargetRef(value=target),
                    sensitive=True,
                )
                for target in dict.fromkeys(discovery.input_targets.values())
            ),
            success_templates=tuple(success),
            outputs=outputs,
        )
    )
    profile = ApplicationProfile.model_validate(
        {
            "profile_id": family,
            "application_family": family,
            "variant": "generated-v1",
            "entry_point": entry_point,
            "target_bindings": tuple(by_target.values()),
        }
    )
    return CapabilityPackage(
        capability=built.definition,
        profile=profile,
        identity=discovery.identity,
        binding_evidence=tuple(
            BindingEvidence(
                target=binding.semantic_target.value,
                observation_fingerprint=item.structural_fingerprint,
            )
            for item, binding in zip(discovery.observed_bindings, bindings, strict=True)
        ),
        entry_point=profile.entry_point,
    )
