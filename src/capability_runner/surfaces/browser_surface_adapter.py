"""Concrete Playwright browser surface adapter."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.async_api import (
    Browser,
    BrowserContext,
    ElementHandle,
    Frame,
    FrameLocator,
    JSHandle,
    Locator,
    Page,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import HttpUrl

from capability_runner.contracts.actions import (
    ActionSpec,
    FillAction,
    NavigateAction,
    WaitAction,
)
from capability_runner.contracts.browser_discovery import (
    BrowserObservation,
    BrowserScope,
    InteractiveElement,
)
from capability_runner.contracts.observations import (
    ObservationSpec,
    OutcomeObservation,
    PageObservation,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    FrameContext,
    InputValueRef,
    LabelLocator,
    LiteralValue,
    LocatorCandidate,
    LocatorResolutionOutcome,
    RoleLocator,
    RowMatch,
    RowScope,
    SemanticTargetRef,
    SurfaceActionOutcome,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    SurfaceView,
    TargetInspectionResult,
)
from capability_runner.surfaces.browser_observation import (
    fingerprint,
    method_allowed,
    origin_of,
    safe_slug,
    within_scope,
)

MAX_OPERATOR_VIEW_WIDTH = 1600
MAX_OPERATOR_VIEW_HEIGHT = 1200
MAX_OPERATOR_VIEW_BYTES = 2_000_000


class BrowserSurfaceError(RuntimeError):
    """Raised for invalid session lifecycle or unsupported resolution states."""


class BrowserSurfaceSessionClosedError(BrowserSurfaceError):
    """Raised when a closed or unknown surface session is used."""


class BrowserSurfaceTargetError(BrowserSurfaceError):
    """Raised when a semantic target is missing from the profile."""


_LocatorScope = Any


def _empty_input_values() -> dict[str, str]:
    return {}


@dataclass(slots=True)
class _SessionState:
    context: BrowserContext
    page: Page
    profile: ApplicationProfile
    input_values: dict[str, str] = field(default_factory=_empty_input_values)
    observation_id: str = ""
    ref_counter: int = 0
    observed: dict[str, InteractiveElement] = field(
        default_factory=lambda: dict[str, InteractiveElement]()
    )
    nodes: dict[str, ElementHandle] = field(default_factory=lambda: dict[str, ElementHandle]())
    revisions: list[JSHandle] = field(default_factory=lambda: list[JSHandle]())
    browser_scope: BrowserScope | None = None
    context_id: str = field(default_factory=lambda: uuid4().hex)
    page_id: str = field(default_factory=lambda: uuid4().hex)
    human_sink: Callable[[dict[str, str | bool]], None] | None = None
    human_capture_installed: bool = False
    human_event_count: int = 0
    frame_ids: dict[Frame, str] = field(default_factory=lambda: dict[Frame, str]())


# No values, text, selectors, URLs, or keystrokes cross this binding. Event capture
# is passive and best effort; only fresh resume validation can authorize automation.
_HUMAN_CAPTURE_SCRIPT = """(() => {
  if (window.__crHumanCaptureInstalled) return;
  window.__crHumanCaptureInstalled = true;
  for (const kind of ['click', 'change']) document.addEventListener(kind, event => {
    if (!event.isTrusted) return;
    const target = event.target;
    if (!(target instanceof Element)) return;
    const type = (target.getAttribute('type') || '').toLowerCase();
    const autocomplete = (target.getAttribute('autocomplete') || '').toLowerCase();
    if (['password', 'hidden'].includes(type) || autocomplete === 'one-time-code') return;
    const tag = target.tagName.toLowerCase();
    window.__crHumanObserved({kind, tag: ['a', 'button', 'input', 'select', 'textarea']
      .includes(tag) ? tag : 'element', value_redacted: kind === 'change'}).catch(() => {});
  }, true);
})()"""


class BrowserSurfaceAdapter:
    def __init__(self, *, headless: bool = True, default_timeout_ms: int = 2_000) -> None:
        self._headless = headless
        self._default_timeout_ms = default_timeout_ms
        self._playwright = None
        self._browser: Browser | None = None
        self._sessions: dict[str, _SessionState] = {}
        self._lock = asyncio.Lock()

    async def open_surface_session(
        self,
        profile: ApplicationProfile,
        *,
        browser_scope: BrowserScope | None = None,
    ) -> SurfaceSessionRef:
        browser = await self._ensure_browser()
        context = await browser.new_context(service_workers="block")
        if browser_scope is not None:
            if not within_scope(str(profile.entry_point), browser_scope):
                await context.close()
                raise BrowserSurfaceError("APPLICATION_NOT_ALLOWED")
            await self._install_scope(context, browser_scope)
        context.set_default_timeout(self._default_timeout_ms)
        context.set_default_navigation_timeout(self._default_timeout_ms)
        page = await context.new_page()
        page.set_default_timeout(self._default_timeout_ms)

        try:
            await page.goto(
                str(profile.entry_point),
                wait_until="domcontentloaded",
                timeout=self._default_timeout_ms,
            )
            await page.wait_for_load_state("networkidle", timeout=self._default_timeout_ms)
        except Exception:
            await context.close()
            raise

        session_ref = SurfaceSessionRef(surface_session_id=uuid4().hex)
        async with self._lock:
            self._sessions[session_ref.surface_session_id] = _SessionState(
                context=context,
                page=page,
                profile=profile,
                browser_scope=browser_scope,
            )
        return session_ref

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        state = await self._require_session(session)
        visible_text = await self._collect_visible_text(state.page)
        title = await state.page.title()
        url = state.page.url
        normalized = visible_text.casefold()

        for rule in state.profile.observation_rules:
            if rule.text.casefold() in normalized:
                return OutcomeObservation(
                    kind="outcome",
                    outcome=rule.outcome,
                    summary=rule.summary,
                    details=visible_text,
                )

        page_url = HttpUrl(url)
        return PageObservation(
            kind="page",
            url=page_url,
            title=title or None,
            visible_text=visible_text,
        )

    async def constrain_browser(self, session: SurfaceSessionRef, scope: BrowserScope) -> None:
        state = await self._require_session(session)
        state.browser_scope = scope
        await self._install_scope(state.context, scope)

    @staticmethod
    async def _install_scope(context: BrowserContext, scope: BrowserScope) -> None:
        async def route_request(route: Any) -> None:
            request = route.request
            if not method_allowed(request.method, request.url, scope):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_request)

    async def observe_browser(self, session: SurfaceSessionRef) -> BrowserObservation:
        state = await self._require_session(session)
        for revision in state.revisions:
            try:
                await revision.evaluate("r => r.observer.disconnect()")
                await revision.dispose()
            except Exception:
                pass
        for node in state.nodes.values():
            await node.dispose()
        state.revisions.clear()
        state.nodes.clear()
        state.observed.clear()
        state.observation_id = uuid4().hex
        elements: list[InteractiveElement] = []
        headings: list[str] = []
        truncated = False
        for frame in state.page.frames[:4]:
            if origin_of(frame.url) != origin_of(state.page.url):
                continue
            if frame != state.page.main_frame and not frame.name:
                continue
            revision = await frame.evaluate_handle(_MUTATION_WATCH)
            state.revisions.append(revision)
            raw: dict[str, Any] = await frame.evaluate(_INTERACTIVE_SNAPSHOT)
            headings.extend(raw["headings"])
            truncated |= bool(raw["truncated"])
            for item in raw["elements"]:
                if len(elements) >= 64:
                    truncated = True
                    break
                state.ref_counter += 1
                ref = f"e{state.ref_counter}"
                role, name, label = item["role"], item["name"], item["label"]
                target = SemanticTargetRef(
                    value=f"page.{safe_slug(role)}.{safe_slug(label or name)}"
                )
                frame_context = FrameContext(name=frame.name) if frame.name else None
                candidates: tuple[LocatorCandidate, ...]
                if item["action_kind"] and name:
                    candidates = (RoleLocator(role=role, name=name, exact=True),)
                elif item["aria_label"]:
                    candidates = (LabelLocator(label=item["aria_label"], exact=True),)
                else:
                    candidates = (CssLocator(selector=item["path"]),)
                row_scope = None
                if item.get("row_value") and item["action_kind"] == "click":
                    row_scope = RowScope(
                        table_context=CssLocator(selector=item["table_path"]),
                        row_match=RowMatch(
                            column=item["row_column"], value=LiteralValue(value=item["row_value"])
                        ),
                    )
                binding = BrowserTargetBinding(
                    semantic_target=target,
                    frame=frame_context,
                    locator_candidates=candidates,
                    row_scope=row_scope,
                    description=(label or name or role)[:160],
                    observation_id=state.observation_id,
                    ephemeral_ref=ref,
                )
                scope = await self._resolve_scope(state.page, binding)
                locator, resolved = await self._resolve_locator(scope, binding, state)
                count = (
                    1
                    if locator is not None
                    else (2 if resolved.status == "TARGET_AMBIGUOUS" else 0)
                )
                node = await frame.locator(item["path"]).element_handle()
                state.nodes[ref] = node
                element = InteractiveElement(
                    ephemeral_ref=ref,
                    role=role,
                    accessible_name=name,
                    label=label,
                    input_type=item["input_type"],
                    current_value_state=item["value_state"],
                    enabled=item["enabled"],
                    nearby_text_summary=item["nearby"],
                    text=item["text"],
                    frame_identity=frame.name or "main",
                    structural_fingerprint=fingerprint(json.dumps([role, label, item["path"]])),
                    action_kind=item["action_kind"],
                    destination=item["destination"],
                    method=item["method"],
                    binding=binding,
                    match_count=count,
                )
                elements.append(element)
                state.observed[ref] = element
        return BrowserObservation(
            observation_id=state.observation_id,
            title=(await state.page.title())[:160],
            origin=origin_of(state.page.url),
            path=re.sub(r"\d+", "_", urlsplit(state.page.url).path)[:300],
            headings=tuple(headings[:8]),
            elements=tuple(elements),
            truncated=truncated,
        )

    async def inspect_bound_element(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> InteractiveElement:
        state = await self._require_session(session)
        scope = await self._resolve_scope(state.page, binding)
        locator, resolution = await self._resolve_locator(scope, binding, state)
        if locator is None:
            raise BrowserSurfaceError(resolution.status)
        observation = await self.observe_browser(session)
        for element in observation.elements:
            if element.frame_identity != (binding.frame.name if binding.frame else "main"):
                continue
            node = state.nodes[element.ephemeral_ref]
            if await locator.evaluate("(el, expected) => el === expected", node):
                return element
        raise BrowserSurfaceError("TARGET_NOT_FOUND")

    async def resolve_observed(
        self,
        session: SurfaceSessionRef,
        observation_id: str,
        element_ref: str,
    ) -> InteractiveElement:
        state = await self._require_session(session)
        if observation_id != state.observation_id or element_ref not in state.observed:
            raise BrowserSurfaceError("STALE_ELEMENT_REF")
        try:
            for revision in state.revisions:
                if not await revision.evaluate("r => r.version === 0 && r.document === document"):
                    raise BrowserSurfaceError("STALE_ELEMENT_REF")
            node = state.nodes[element_ref]
            if not await node.is_visible():
                raise BrowserSurfaceError("STALE_ELEMENT_REF")
        except Exception as error:
            raise BrowserSurfaceError("STALE_ELEMENT_REF") from error
        element = state.observed[element_ref]
        if element.match_count != 1 or element.binding is None:
            raise BrowserSurfaceError("TARGET_AMBIGUOUS")
        scope = await self._resolve_scope(state.page, element.binding)
        locator, _ = await self._resolve_locator(scope, element.binding, state)
        if locator is None or not await locator.evaluate("(el, expected) => el === expected", node):
            raise BrowserSurfaceError("STALE_ELEMENT_REF")
        return element

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        state = await self._require_session(session)
        if binding.observation_id and binding.ephemeral_ref:
            try:
                await self.resolve_observed(session, binding.observation_id, binding.ephemeral_ref)
            except BrowserSurfaceError:
                return self._result(action, binding, "TARGET_NOT_FOUND", "Stale element reference")
        elif binding.semantic_target.value not in {
            target.semantic_target.value for target in state.profile.target_bindings
        }:
            return self._result(action, binding, "TARGET_NOT_FOUND", "Unknown semantic target")

        page = state.page
        try:
            if isinstance(action, NavigateAction):
                await page.goto(
                    str(action.url), wait_until="domcontentloaded", timeout=self._default_timeout_ms
                )
                await page.wait_for_load_state("networkidle", timeout=self._default_timeout_ms)
                return self._result(
                    action,
                    binding,
                    "APPLIED",
                    f"Navigated to {action.url}",
                    await self.observe_surface(session),
                )

            if isinstance(action, WaitAction):
                await asyncio.sleep(action.seconds)
                return self._result(
                    action,
                    binding,
                    "APPLIED",
                    f"Waited {action.seconds:.3f} seconds",
                    await self.observe_surface(session),
                )

            scope = await self._resolve_scope(state.page, binding)
            locator, resolution = await self._resolve_locator(scope, binding, state)
            if locator is None:
                outcome = (
                    "TARGET_NOT_FOUND" if resolution.status == "RESOLVED" else resolution.status
                )
                return self._result(
                    action, binding, outcome, resolution_message(resolution, binding)
                )

            if isinstance(action, FillAction):
                fill_value = action.value.get_secret_value()
                await locator.fill(fill_value)
                state.input_values[binding.semantic_target.value.rsplit(".", 1)[-1]] = fill_value
                return self._result(
                    action,
                    binding,
                    "APPLIED",
                    f"Filled {binding.semantic_target.value}",
                    await self.observe_surface(session),
                )

            try:
                await locator.click(timeout=self._default_timeout_ms)
            except PlaywrightTimeoutError:
                return self._result(
                    action,
                    binding,
                    "SURFACE_TIMEOUT",
                    f"Timed out while executing {binding.semantic_target.value}",
                )
            return self._result(
                action,
                binding,
                "APPLIED",
                f"Clicked {binding.semantic_target.value}",
                await self.observe_surface(session),
            )

        except BrowserSurfaceError as error:
            return self._result(action, binding, "TARGET_NOT_FOUND", str(error))

        except PlaywrightTimeoutError:
            return self._result(
                action,
                binding,
                "SURFACE_TIMEOUT",
                f"Timed out while executing {binding.semantic_target.value}",
            )

        return self._result(
            action, binding, "TARGET_NOT_ACTIONABLE", f"Unsupported action {action.kind}"
        )

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        state = await self._require_session(session)
        try:
            scope = await self._resolve_scope(state.page, binding)
            locator, resolution = await self._resolve_locator(scope, binding, state)
        except BrowserSurfaceError:
            return TargetInspectionResult(
                outcome="UNAVAILABLE",
                target=binding.semantic_target,
                summary="Target inspection is unavailable.",
            )
        if locator is None:
            outcome = (
                "TARGET_AMBIGUOUS" if resolution.status == "TARGET_AMBIGUOUS" else "NOT_VISIBLE"
            )
            return TargetInspectionResult(
                outcome=outcome,
                target=binding.semantic_target,
                summary=resolution_message(resolution, binding),
            )
        try:
            if not await locator.is_visible():
                return TargetInspectionResult(
                    outcome="NOT_VISIBLE",
                    target=binding.semantic_target,
                    summary="Target is not visible.",
                )
            return TargetInspectionResult(
                outcome="VISIBLE",
                target=binding.semantic_target,
                text=(await locator.inner_text()).strip() or None,
                summary="Target is visible.",
            )
        except PlaywrightTimeoutError:
            return TargetInspectionResult(
                outcome="UNAVAILABLE",
                target=binding.semantic_target,
                summary="Target inspection timed out.",
            )

    async def capture_failure_evidence(
        self, session: SurfaceSessionRef
    ) -> SurfaceFailureEvidence | None:
        observation = await self.observe_surface(session)
        if isinstance(observation, PageObservation):
            return SurfaceFailureEvidence(
                kind="failure",
                summary="Surface snapshot captured",
                details={
                    "url": str(observation.url) if observation.url is not None else "",
                    "title": observation.title or "",
                    "visible_text": observation.visible_text[:500],
                },
            )

        if isinstance(observation, OutcomeObservation):
            return SurfaceFailureEvidence(
                kind="failure",
                summary=observation.summary,
                details={"visible_text": observation.details or ""},
            )

        return SurfaceFailureEvidence(
            kind="failure",
            summary=observation.message,
            details={
                "dialog_type": observation.dialog_type,
                "blocking": str(observation.blocking).lower(),
            },
        )

    async def capture_view(self, session: SurfaceSessionRef) -> SurfaceView:
        state = await self._require_session(session)
        viewport = state.page.viewport_size
        if viewport is None:
            raise BrowserSurfaceError("browser viewport is unavailable")
        width = min(viewport["width"], MAX_OPERATOR_VIEW_WIDTH)
        height = min(viewport["height"], MAX_OPERATOR_VIEW_HEIGHT)
        content = await state.page.screenshot(
            type="png",
            animations="allow",
            caret="initial",
            clip={"x": 0, "y": 0, "width": width, "height": height},
        )
        if len(content) > MAX_OPERATOR_VIEW_BYTES:
            raise BrowserSurfaceError("operator view exceeds the bounded response size")
        return SurfaceView(
            surface_session=session,
            content=content,
            width=width,
            height=height,
        )

    async def browser_identity(self, session: SurfaceSessionRef) -> dict[str, str | bool]:
        state = await self._require_session(session)
        return {
            "surface_session_id": session.surface_session_id,
            "browser_context_id": state.context_id,
            "page_id": state.page_id,
            "browser_headless": self._headless,
        }

    async def focus_browser(self, session: SurfaceSessionRef) -> None:
        state = await self._require_session(session)
        await state.page.bring_to_front()

    async def start_human_observation(
        self,
        session: SurfaceSessionRef,
        sink: Callable[[dict[str, str | bool]], None],
    ) -> None:
        state = await self._require_session(session)

        def observed(frame: Frame, kind: str, tag: str, redacted: bool) -> None:
            if state.human_sink is None or state.human_event_count >= 200:
                return
            state.human_event_count += 1
            state.human_sink(
                {
                    "surface_session_id": session.surface_session_id,
                    "page_id": state.page_id,
                    "frame_id": state.frame_ids.setdefault(frame, uuid4().hex),
                    "action_type": kind,
                    "element_type": tag,
                    "value_redacted": redacted,
                }
            )

        if not state.human_capture_installed:

            def on_event(source: dict[str, Any], payload: Any) -> None:
                if source.get("page") is not state.page or not isinstance(payload, dict):
                    return
                safe_payload = cast(dict[str, object], payload)
                kind, tag = safe_payload.get("kind"), safe_payload.get("tag")
                if not isinstance(kind, str) or not isinstance(tag, str):
                    return
                if kind not in {"click", "change"}:
                    return
                if tag not in {"a", "button", "input", "select", "textarea", "element"}:
                    return
                observed(source["frame"], kind, tag, kind == "change")

            # Playwright's binding callback return annotation is incomplete.
            await state.page.expose_binding("__crHumanObserved", on_event)  # pyright: ignore[reportUnknownMemberType]
            await state.page.add_init_script(_HUMAN_CAPTURE_SCRIPT)
            for frame in state.page.frames:
                await frame.evaluate(_HUMAN_CAPTURE_SCRIPT)
            state.page.on(
                "framenavigated", lambda frame: observed(frame, "navigation", "frame", False)
            )
            state.human_capture_installed = True
        state.human_sink = sink

    async def stop_human_observation(self, session: SurfaceSessionRef) -> None:
        # Disable even if the physical window was closed. Never replace its page.
        state = self._sessions.get(session.surface_session_id)
        if state is not None:
            state.human_sink = None

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        async with self._lock:
            state = self._sessions.pop(session.surface_session_id, None)
        if state is None:
            raise BrowserSurfaceSessionClosedError(
                f"surface session {session.surface_session_id} is closed"
            )
        await state.context.close()

    async def aclose(self) -> None:
        async with self._lock:
            states = list(self._sessions.values())
            self._sessions.clear()

        for state in states:
            await state.context.close()

        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def _ensure_browser(self) -> Browser:
        if self._browser is not None:
            return self._browser

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        return self._browser

    async def _require_session(self, session: SurfaceSessionRef) -> _SessionState:
        async with self._lock:
            state = self._sessions.get(session.surface_session_id)
        if state is None or state.page.is_closed():
            raise BrowserSurfaceSessionClosedError(
                f"surface session {session.surface_session_id} is closed"
            )
        return state

    async def _resolve_scope(self, page: Page, binding: BrowserTargetBinding) -> _LocatorScope:
        if binding.frame is None:
            return page

        frame = await self._require_frame(page, binding.frame)
        return frame

    async def _require_frame(self, page: Page, frame_context: FrameContext) -> FrameLocator:
        selector = f'iframe[name="{frame_context.name}"]'
        try:
            await page.wait_for_selector(selector, timeout=self._default_timeout_ms)
        except PlaywrightTimeoutError as error:
            raise BrowserSurfaceError(f"frame {frame_context.name} is not available") from error
        frame_locator = page.frame_locator(selector)
        frame = page.frame(name=frame_context.name)
        if frame is None:
            raise BrowserSurfaceError(f"frame {frame_context.name} is not available")
        return frame_locator

    async def _resolve_locator(
        self,
        scope: _LocatorScope,
        binding: BrowserTargetBinding,
        state: _SessionState,
    ) -> tuple[Locator | None, LocatorResolutionOutcome]:
        if binding.row_scope is None:
            return await self._resolve_candidates(scope, binding.locator_candidates)

        row_locator, resolution = await self._resolve_row_scope(scope, binding.row_scope, state)
        if row_locator is None:
            return None, resolution

        return await self._resolve_candidates(row_locator, binding.locator_candidates)

    async def _resolve_row_scope(
        self,
        scope: _LocatorScope,
        row_scope: RowScope,
        state: _SessionState,
    ) -> tuple[Locator | None, LocatorResolutionOutcome]:
        table_locator = (
            scope
            if row_scope.table_context is None
            else self._locator_from_candidate(scope, row_scope.table_context)
        )
        table_count = await table_locator.count()
        if table_count == 0:
            return None, LocatorResolutionOutcome(status="TARGET_NOT_FOUND")
        if table_count > 1:
            return None, LocatorResolutionOutcome(status="TARGET_AMBIGUOUS")

        expected_value = self._resolve_row_value(row_scope, state)
        rows = table_locator.locator("tbody tr")
        row_count = await rows.count()
        matches: list[Locator] = []

        headers = [
            header.strip() for header in await table_locator.locator("thead th").all_inner_texts()
        ]
        if not headers:
            headers = [
                header.strip() for header in await table_locator.locator("th").all_inner_texts()
            ]

        column_index = self._column_index(headers, row_scope.row_match.column)
        for index in range(row_count):
            row = rows.nth(index)
            cell_texts = [cell.strip() for cell in await row.locator("td").all_inner_texts()]
            if column_index >= len(cell_texts):
                continue
            if cell_texts[column_index] == expected_value:
                matches.append(row)

        if not matches:
            return None, LocatorResolutionOutcome(status="TARGET_NOT_FOUND")
        if len(matches) > 1:
            return None, LocatorResolutionOutcome(status="TARGET_AMBIGUOUS")
        return matches[0], LocatorResolutionOutcome(status="RESOLVED", matched_candidate_index=0)

    async def _resolve_candidates(
        self,
        scope: _LocatorScope,
        candidates: tuple[LocatorCandidate, ...],
    ) -> tuple[Locator | None, LocatorResolutionOutcome]:
        for index, candidate in enumerate(candidates):
            locator = self._locator_from_candidate(scope, candidate)
            count = await locator.count()
            if count == 0:
                continue
            if count > 1:
                return None, LocatorResolutionOutcome(
                    status="TARGET_AMBIGUOUS", matched_candidate_index=index
                )
            return locator, LocatorResolutionOutcome(
                status="RESOLVED", matched_candidate_index=index
            )
        return None, LocatorResolutionOutcome(status="TARGET_NOT_FOUND")

    def _locator_from_candidate(self, scope: _LocatorScope, candidate: LocatorCandidate) -> Locator:
        if isinstance(candidate, RoleLocator):
            return scope.get_by_role(candidate.role, name=candidate.name, exact=candidate.exact)
        if isinstance(candidate, LabelLocator):
            return scope.get_by_label(candidate.label, exact=candidate.exact)
        if isinstance(candidate, CssLocator):
            return scope.locator(candidate.selector)

        return scope.get_by_text(candidate.text, exact=candidate.exact)

    def _resolve_row_value(self, row_scope: RowScope, state: _SessionState) -> str:
        value = row_scope.row_match.value
        if isinstance(value, InputValueRef):
            try:
                return state.input_values[value.name]
            except KeyError as exc:
                raise BrowserSurfaceError(f"missing input value {value.name}") from exc
        if value.kind == "literal":
            return value.value
        raise BrowserSurfaceError("unsupported row match value")

    def _column_index(self, headers: list[str], column: str) -> int:
        for index, header in enumerate(headers):
            if header.casefold() == column.casefold():
                return index
        raise BrowserSurfaceError(f"column {column} not found")

    async def _collect_visible_text(self, page: Page) -> str:
        parts: list[str] = []
        body_text = await page.locator("body").inner_text()
        if body_text.strip():
            parts.append(body_text.strip())

        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                frame_body = frame.locator("body")
                if await frame_body.count() == 0:
                    continue
                text = await frame_body.inner_text()
            except Exception:
                continue
            frame_label = frame.name or "unnamed-frame"
            if text.strip():
                parts.append(f"[frame:{frame_label}] {text.strip()}")

        return "\n\n".join(parts)

    def _result(
        self,
        action: ActionSpec,
        binding: BrowserTargetBinding,
        outcome: SurfaceActionOutcome,
        summary: str,
        observation: ObservationSpec | None = None,
    ) -> SurfaceActionResult:
        return SurfaceActionResult(
            outcome=outcome,
            summary=summary,
            action=action,
            observation=observation,
            resolved_target=binding.semantic_target,
        )


def resolution_message(resolution: LocatorResolutionOutcome, binding: BrowserTargetBinding) -> str:
    if resolution.status == "TARGET_NOT_FOUND":
        return f"No locator candidates matched {binding.semantic_target.value}"
    if resolution.status == "TARGET_AMBIGUOUS":
        return (
            f"Locator candidate {resolution.matched_candidate_index} was ambiguous for "
            f"{binding.semantic_target.value}"
        )
    return f"Resolved {binding.semantic_target.value}"


_MUTATION_WATCH = """() => {
    const state = {version: 0, document};
    state.observer = new MutationObserver(() => state.version++);
    state.observer.observe(document.documentElement,
        {subtree: true, childList: true, attributes: true, characterData: true});
    return state;
}"""

# Adapter-owned fixed code. Never taken from a model response or application text.
_INTERACTIVE_SNAPSHOT = r"""() => {
  const clean = (s, n=160) => String(s || '').replace(/\s+/g, ' ').trim().slice(0,n);
  const visible = el => !!el.getClientRects().length &&
    getComputedStyle(el).visibility !== 'hidden' &&
    !el.closest('[hidden],[aria-hidden="true"],script,style,noscript');
  const path = el => {
    if (el.id && /^[a-zA-Z][a-zA-Z_-]{0,60}$/.test(el.id)) return '#' + el.id;
    const parts=[];
    while(el && el.tagName !== 'BODY') {
      let i=1, sib=el.previousElementSibling;
      while(sib) {if(sib.tagName===el.tagName) i++; sib=sib.previousElementSibling;}
      parts.unshift(el.tagName.toLowerCase()+':nth-of-type('+i+')'); el=el.parentElement;
    }
    return 'body > '+parts.join(' > ');
  };
  const elements=[];
  const nodes=document.querySelectorAll('input,textarea,button,a[href],[role="button"],'
    +'[role="link"],output,dd,p > span,td,[role="status"],[role="alert"]');
  let scanned=0;
  for(const el of nodes) {
    if(++scanned > 600 || elements.length >= 64) break;
    if(!visible(el)) continue;
    const tag=el.tagName.toLowerCase(), type=clean(el.type,30);
    if(type==='hidden' || type==='password' || type==='file') continue;
    if(['td','dd','span'].includes(tag) && el.querySelector('a,button,input,output,span')) continue;
    const labelEl=el.labels && el.labels[0];
    const labelled=el.getAttribute('aria-labelledby');
    const ariaLabel=clean(el.getAttribute('aria-label') ||
      (labelled && document.getElementById(labelled)?.innerText));
    let label=ariaLabel || clean(labelEl?.innerText);
    if(!label && tag==='dd') label=clean(el.previousElementSibling?.innerText);
    if(!label && tag==='span') label=clean(el.parentElement?.querySelector('strong')?.innerText);
    if(!label && tag==='td') label=clean(
      el.closest('table')?.querySelectorAll('thead th')[el.cellIndex]?.innerText);
    if(/password|secret|token|credential|social security|email/i.test(label)) continue;
    const text=clean(el.innerText,256);
    const role=clean(el.getAttribute('role') ||
      (tag==='a'?'link':tag==='button'?'button':['input','textarea'].includes(tag)?'textbox':'text'),40);
    const name=ariaLabel || clean(labelEl?.innerText) ||
      (['link','button'].includes(role)?clean(text || el.value):label);
    const action_kind=role==='textbox' && ['text','search','number','tel',''].includes(type)?'fill':
      ['link','button'].includes(role)?'click':null;
    if(!action_kind && (!text || !label)) continue;
    const form=el.form;
    const destination=tag==='a'?el.href:form?form.action:null;
    const method=tag==='a'?'GET':form?String(form.method || 'get').toUpperCase():'';
    const row=el.closest('tbody tr'), table=row?.closest('table');
    const rowCell=row?.querySelector('td'), rowHeader=table?.querySelector('thead th');
    const nearby=clean(row?.innerText || label,200);
    const item={role,name,label:label || name,input_type:type,
      value_state:action_kind==='fill'?(el.value?'set':'empty'):'not_applicable',
      enabled:!el.disabled && el.getAttribute('aria-disabled')!=='true',
      text:action_kind==='fill'?'':text, nearby, action_kind,destination,method,
      path:path(el),aria_label:ariaLabel};
    if(rowCell && rowHeader && table) Object.assign(item,
      {row_value:clean(rowCell.innerText),row_column:clean(rowHeader.innerText),table_path:path(table)});
    if(item.path.length<=240 && (!item.table_path || item.table_path.length<=240))
      elements.push(item);
  }
  return {elements, headings:[...document.querySelectorAll('h1,h2,h3')].filter(visible)
    .slice(0,8).map(el=>clean(el.innerText)), truncated:scanned>600 || elements.length>=64};
}"""
