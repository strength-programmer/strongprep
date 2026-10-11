"""Builds the planning context, runs the provider, then HARD-validates the result before it is saved."""
import math
from datetime import date

from app.config import Settings
from app.data.reference import IMPLEMENTS, TASKS
from app.integrations.ai import (MINUTES_PER_SET, MINUTES_WARMUP, ProviderError, ProviderUnavailable,
                                 estimate_minutes, get_provider)

BANNED_PHRASES = ["diagnos", "rehabilitat", "guarantee", "will win", "readiness score", "readiness percent", "% ready"]
MAX_WEEKS = 16


class PlanError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None, status: int = 422):
        super().__init__(message)
        self.errors = errors or []
        self.status = status


def weeks_until(competition, today: date) -> int:
    days = (competition.start_date - today).days
    if competition.status != "upcoming" or days <= 0:
        raise PlanError("A plan can only be generated for an upcoming competition that has not started.")
    return max(1, min(MAX_WEEKS, days // 7 or 1))


def build_context(profile, equipment: list, templates: list, assessment_result: dict, competition, today: date) -> dict:
    missing = []
    if not profile or not profile.days_per_week:
        missing.append("days_per_week")
    if not profile or not profile.session_minutes:
        missing.append("session_minutes")
    if missing:
        raise PlanError("Complete your availability before generating a plan.", [f"Missing: {m}" for m in missing])
    if assessment_result["eligibility"]["status"] == "ineligible":
        raise PlanError("You appear ineligible for this division; resolve eligibility before generating a plan.",
                        [c["detail"] for c in assessment_result["eligibility"]["checks"] if c["result"] == "fail"])

    regular = {e.implement for e in equipment if e.access == "regular"}
    occasional = {e.implement for e in equipment if e.access == "occasional"}
    avoid = set(profile.avoid_exercises or [])
    pain = set(profile.pain_flags or [])
    usable, paused = [], []
    for t in templates:
        if t.key in avoid or (t.task_key and t.task_key in avoid):
            paused.append({"item": t.name, "reason": "On your avoid list."})
            continue
        hit = pain & set(t.body_areas or [])
        if hit:
            paused.append({"item": t.name, "reason": f"Paused because of your pain flag ({', '.join(sorted(hit))}); seek professional review."})
            continue
        need = set(t.equipment or [])
        access = "regular" if need <= regular else "occasional" if need <= regular | occasional else None
        if access:
            usable.append({"key": t.key, "name": t.name, "category": t.category, "equipment": list(t.equipment or []),
                           "demand_tags": list(t.demand_tags or []), "task_key": t.task_key, "sets": t.sets, "reps": t.reps,
                           "intensity": t.intensity, "access": access, "body_areas": list(t.body_areas or []),
                           "review_status": t.review_status, "template_version": t.template_version})
    events = []
    for e in assessment_result["events"]:
        task = TASKS.get(e["task_key"], {})
        events.append({
            "event_id": e["event_id"], "name": e["event_name"], "task_key": e["task_key"], "family": task.get("family"),
            "implement_label": IMPLEMENTS.get(task.get("implement"), "unknown"), "priority": e["priority"],
            "status": e["status"], "status_label": e["status_label"], "detail": e["detail"],
            "equipment_flags": e["equipment"]["flags"], "access": e["equipment"]["access"], "next_step": e["next_step"],
        })
    return {
        "competition_title": competition.title, "weeks_total": weeks_until(competition, today),
        "days_per_week": profile.days_per_week, "session_minutes": profile.session_minutes,
        "events": events, "templates": usable, "paused": paused,
    }


def validate_plan(plan: dict, ctx: dict) -> list[str]:
    """Hard checks. Any returned error blocks saving."""
    errs: list[str] = []
    if not isinstance(plan, dict):
        return ["Plan is not an object."]
    tmpl = {t["key"]: t for t in ctx["templates"]}
    event_ids = {e["event_id"] for e in ctx["events"]}
    weeks = plan.get("weeks")
    if not isinstance(weeks, list) or not weeks:
        return ["Plan has no weeks."]
    if plan.get("weeks_total") != ctx["weeks_total"] or len(weeks) != ctx["weeks_total"]:
        errs.append(f"Plan must have exactly {ctx['weeks_total']} weeks.")
    for w in weeks:
        sessions = w.get("sessions") if isinstance(w, dict) else None
        if not isinstance(sessions, list):
            errs.append("A week is missing its sessions list.")
            continue
        wk = w.get("week")
        if len(sessions) > ctx["days_per_week"]:
            errs.append(f"Week {wk}: {len(sessions)} sessions exceeds {ctx['days_per_week']} available days.")
        if not sessions:
            errs.append(f"Week {wk}: no sessions.")
        access_sessions = 0
        for s in sessions:
            sid = s.get("id", "?")
            exs = s.get("exercises") or []
            if not exs:
                errs.append(f"Session {sid}: no exercises.")
            if s.get("access_session"):
                access_sessions += 1
            for ev_id in s.get("focus_event_ids", []):
                if ev_id not in event_ids:
                    errs.append(f"Session {sid}: unknown event id {ev_id}.")
            sets_list = []
            for x in exs:
                t = tmpl.get(x.get("template_key"))
                if t is None:
                    errs.append(f"Session {sid}: exercise '{x.get('template_key')}' is not an allowed template (unavailable equipment, avoided, paused, or unknown).")
                    continue
                if t["access"] == "occasional" and not s.get("access_session"):
                    errs.append(f"Session {sid}: '{t['name']}' needs occasional-access equipment but the session is not marked as an access session.")
                sets = x.get("sets")
                if not isinstance(sets, int) or sets < 1 or sets > 10:
                    errs.append(f"Session {sid}: invalid set count for '{t['name']}'.")
                    continue
                sets_list.append(sets)
            if sets_list:
                est = estimate_minutes(sets_list)
                if est > ctx["session_minutes"]:
                    errs.append(f"Session {sid}: needs ~{est} min but you have {ctx['session_minutes']}.")
                if s.get("estimated_minutes") != est:
                    errs.append(f"Session {sid}: estimated_minutes should be {est}.")
        if access_sessions > 1:
            errs.append(f"Week {wk}: more than one access session.")
    needed = {e["event_id"] for e in ctx["events"] if e["status"] != "demonstrated"}
    explained = {x.get("event_id") for x in plan.get("explanations", [])}
    for miss in sorted(needed - explained):
        errs.append(f"Missing explanation for event {miss}.")
    for x in plan.get("explanations", []):
        if x.get("event_id") not in event_ids:
            errs.append(f"Explanation references unknown event {x.get('event_id')}.")
    for need in ("missed_sessions", "equipment_changes", "pain"):
        if not (plan.get("rules") or {}).get(need):
            errs.append(f"Missing rule text: {need}.")
    narrative = [str(plan.get("title", ""))]
    narrative += [str(x.get("text", "")) for x in plan.get("explanations", [])]
    narrative += [str(x.get("action", "")) for x in plan.get("practice_needs", [])]
    narrative += [str(s.get("purpose", "")) for w in weeks for s in (w.get("sessions") or [])]
    blob = " ".join(narrative).lower()
    for p in BANNED_PHRASES:
        if p in blob:
            errs.append(f"Unsupported statement detected ('{p}').")
    return errs


def generate_validated_plan(ctx: dict, settings: Settings, provider=None, retries: int = 1) -> tuple[dict, str]:
    try:
        provider = provider or get_provider(settings)
    except ProviderUnavailable as exc:
        raise PlanError(str(exc), status=503)
    last_errors: list[str] = []
    for _ in range(retries + 1):
        try:
            plan = provider.generate_plan(ctx)
        except ProviderUnavailable as exc:
            raise PlanError(str(exc), status=503)
        except ProviderError as exc:
            raise PlanError(str(exc), status=422 if provider.name == "mock" else 502)
        last_errors = validate_plan(plan, ctx)
        if not last_errors:
            plan["provider"] = provider.name
            plan["ai_label"] = {"mock": "Mock AI (not a real model)", "claude": "Generated by Claude, validated by app rules"}.get(
                provider.name, f"Generated by {getattr(provider, 'model', 'an LLM')} via {provider.name}, validated by app rules")
            plan["template_notice"] = "Exercise templates are unreviewed demo samples until a coach reviews them."
            plan["validation"] = {"passed": True, "checked": ["equipment", "schedule", "templates", "explanations", "unsupported claims"]}
            return plan, provider.name
    raise PlanError("The generated plan failed validation and was not saved.", last_errors, status=422)
