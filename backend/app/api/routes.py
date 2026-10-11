from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session, selectinload

from app.api.auth import current_owner, optional_owner
from app.config import Settings, get_settings
from app.data import reference as ref
from app.db import get_db
from app.integrations.ai import ai_status
from app.integrations.search_extract import integration_status
from app.models import (Assessment, AthleteProfile, Competition, CompetitionDivision, EquipmentAccess, EventSpecification,
                        EventSpecRevision, ExerciseTemplate, HistoricalResult, PerformanceRecord, PreparationPlan,
                        SourceEvidence, TrainingLog)
from app.schemas import (AssessmentIn, CompetitionIn, EquipmentItem, EventIn, PerformanceIn, PlanIn, ProfileIn, TargetIn,
                         TrainingLogIn)
from app.services import assessment as assess_svc
from app.services import planning

router = APIRouter()


def d(o) -> dict:
    return {c.key: getattr(o, c.key) for c in inspect(o).mapper.column_attrs}


def now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- status / reference
@router.get("/status")
def status(settings: Settings = Depends(get_settings)):
    return {"mode": settings.app_mode, "ai": ai_status(settings), "integrations": integration_status(),
            "demo_notice": "Local demo mode: fictional competitions, synthetic benchmarks, unreviewed templates, mock AI."
            if settings.is_demo else None}


@router.get("/reference")
def reference(db: Session = Depends(get_db)):
    return {
        "tasks": [{"key": k, **v, "implement_label": ref.IMPLEMENTS[v["implement"]]} for k, v in ref.TASKS.items()],
        "implements": [{"key": k, "label": v} for k, v in ref.IMPLEMENTS.items()],
        "body_areas": ref.BODY_AREAS, "scoring_types": ref.SCORING_TYPES, "source_types": ref.SOURCE_TYPES,
        "templates": [{"key": t.key, "name": t.name, "review_status": t.review_status} for t in db.query(ExerciseTemplate).all()],
    }


# ---------------------------------------------------------------- profile / equipment / performance
def _profile(db, owner):
    return db.query(AthleteProfile).filter_by(owner_id=owner).first()


def _completeness(db, owner, profile) -> dict:
    checks = {
        "body_weight_kg": bool(profile and profile.body_weight_kg), "age": bool(profile and profile.age),
        "division_category": bool(profile and profile.division_category),
        "experience_level": bool(profile and profile.experience_level),
        "availability": bool(profile and profile.days_per_week and profile.session_minutes),
        "equipment": db.query(EquipmentAccess).filter_by(owner_id=owner).count() > 0,
        "performance_records": db.query(PerformanceRecord).filter_by(owner_id=owner).count() > 0,
        "target_competition": bool(profile and profile.target_division_id),
    }
    return {"percent": round(100 * sum(checks.values()) / len(checks)), "checks": checks,
            "missing": [k for k, v in checks.items() if not v]}


@router.get("/athlete-profile")
def get_profile(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    p = _profile(db, owner)
    return {"profile": d(p) if p else None, "completeness": _completeness(db, owner, p)}


@router.put("/athlete-profile")
def put_profile(body: ProfileIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    p = _profile(db, owner)
    if not p:
        p = AthleteProfile(owner_id=owner)
        db.add(p)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return {"profile": d(p), "completeness": _completeness(db, owner, p)}


def _visible_competition(db, owner, cid) -> Competition:
    c = db.get(Competition, cid)
    if not c or (c.owner_id is not None and c.owner_id != owner):
        raise HTTPException(404, "Competition not found.")
    return c


@router.put("/athlete-profile/target")
def set_target(body: TargetIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    comp = _visible_competition(db, owner, body.competition_id)
    div = db.get(CompetitionDivision, body.division_id)
    if not div or div.competition_id != comp.id:
        raise HTTPException(404, "Division not found in that competition.")
    p = _profile(db, owner)
    if not p:
        p = AthleteProfile(owner_id=owner)
        db.add(p)
    p.target_competition_id, p.target_division_id = comp.id, div.id
    db.commit()
    return {"profile": d(p), "completeness": _completeness(db, owner, p)}


@router.get("/equipment")
def get_equipment(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return [d(e) for e in db.query(EquipmentAccess).filter_by(owner_id=owner).order_by(EquipmentAccess.id)]


@router.put("/equipment")
def put_equipment(items: list[EquipmentItem], owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    seen = set()
    for it in items:
        if it.implement not in ref.IMPLEMENTS:
            raise HTTPException(422, f"Unknown implement '{it.implement}'.")
        if it.implement in seen:
            raise HTTPException(422, f"Implement '{it.implement}' listed twice.")
        seen.add(it.implement)
    db.query(EquipmentAccess).filter_by(owner_id=owner).delete()
    for it in items:
        db.add(EquipmentAccess(owner_id=owner, **it.model_dump()))
    db.commit()
    return get_equipment(owner, db)


def _own_record(db, owner, rid) -> PerformanceRecord:
    r = db.get(PerformanceRecord, rid)
    if not r or r.owner_id != owner:
        raise HTTPException(404, "Record not found.")
    return r


@router.get("/performance-records")
def list_records(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return [d(r) for r in db.query(PerformanceRecord).filter_by(owner_id=owner).order_by(PerformanceRecord.record_date.desc(), PerformanceRecord.id.desc())]


@router.post("/performance-records", status_code=201)
def add_record(body: PerformanceIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    r = PerformanceRecord(owner_id=owner, **body.model_dump())
    db.add(r)
    db.commit()
    return d(r)


@router.put("/performance-records/{rid}")
def edit_record(rid: int, body: PerformanceIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    r = _own_record(db, owner, rid)
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    return d(r)


@router.delete("/performance-records/{rid}", status_code=204)
def delete_record(rid: int, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    db.delete(_own_record(db, owner, rid))
    db.commit()


# ---------------------------------------------------------------- competitions
def _comp_summary(c: Competition) -> dict:
    out = d(c)
    out["divisions"] = [{"id": v.id, "name": v.name, "category": v.category, "event_count": len(v.events)} for v in c.divisions]
    out["is_shared_catalog"] = c.owner_id is None
    return out


@router.get("/competitions")
def list_competitions(q: str | None = None, city: str | None = None, date_from: date | None = None,
                      date_to: date | None = None, status: str | None = None,
                      owner: str | None = Depends(optional_owner), db: Session = Depends(get_db)):
    query = db.query(Competition).options(selectinload(Competition.divisions).selectinload(CompetitionDivision.events))
    query = query.filter(or_(Competition.owner_id.is_(None), Competition.owner_id == owner) if owner else Competition.owner_id.is_(None))
    if q:
        query = query.filter(Competition.title.ilike(f"%{q}%"))
    if city:
        query = query.filter(Competition.city.ilike(f"%{city}%"))
    if date_from:
        query = query.filter(Competition.start_date >= date_from)
    if date_to:
        query = query.filter(Competition.start_date <= date_to)
    if status:
        query = query.filter(Competition.status == status)
    return [_comp_summary(c) for c in query.order_by(Competition.start_date)]


def _event_dict(e: EventSpecification, ev_by_event: dict) -> dict:
    out = d(e)
    out["task_label"] = ref.TASKS.get(e.task_key, {}).get("label", e.task_key)
    out["evidence"] = [d(x) for x in ev_by_event.get(e.id, [])]
    return out


@router.get("/competitions/{cid}")
def get_competition(cid: int, owner: str | None = Depends(optional_owner), db: Session = Depends(get_db)):
    c = db.get(Competition, cid)
    if not c or (c.owner_id is not None and c.owner_id != owner):
        raise HTTPException(404, "Competition not found.")
    ev_ids = [e.id for v in c.divisions for e in v.events]
    evidence = db.query(SourceEvidence).filter(SourceEvidence.entity_type == "event", SourceEvidence.entity_id.in_(ev_ids or [0])).all()
    by_event: dict = {}
    for x in evidence:
        by_event.setdefault(x.entity_id, []).append(x)
    comp_ev = db.query(SourceEvidence).filter_by(entity_type="competition", entity_id=c.id).all()
    out = d(c)
    out["is_shared_catalog"] = c.owner_id is None
    out["evidence"] = [d(x) for x in comp_ev]
    out["divisions"] = [{**d(v), "events": [_event_dict(e, by_event) for e in v.events]} for v in c.divisions]
    return out


@router.post("/competitions", status_code=201)
def create_competition(body: CompetitionIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"divisions"})
    comp = Competition(owner_id=owner, last_checked_at=now(), status="upcoming", verification_status="unverified",
                       is_demo=False, **data)
    db.add(comp)
    db.flush()
    db.add(SourceEvidence(entity_type="competition", entity_id=comp.id, field_name="all", url=comp.source_url,
                          retrieved_at=now(), excerpt="Entered manually by the athlete.", review_status="manual_unreviewed"))
    for dv in body.divisions:
        div = CompetitionDivision(competition_id=comp.id, **dv.model_dump(exclude={"events"}))
        db.add(div)
        db.flush()
        for i, ev in enumerate(dv.events):
            e = EventSpecification(division_id=div.id, position=i, verification_status="manual_unreviewed", **ev.model_dump())
            db.add(e)
            db.flush()
            db.add(SourceEvidence(entity_type="event", entity_id=e.id, field_name="all", url=comp.source_url, retrieved_at=now(),
                                  excerpt=ev.original_load_text or "Entered manually; original text not provided.",
                                  review_status="manual_unreviewed"))
    db.commit()
    return get_competition(comp.id, owner, db)


@router.put("/events/{eid}")
def update_event(eid: int, body: EventIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    e = db.get(EventSpecification, eid)
    comp = e.division.competition if e else None
    if not e or comp.owner_id not in (None, owner):
        raise HTTPException(404, "Event not found.")
    if comp.owner_id is None:
        raise HTTPException(403, "Shared catalog events are read-only.")
    new = body.model_dump()
    old = {k: getattr(e, k) for k in new}
    if new == old:
        return d(e)
    db.add(EventSpecRevision(event_id=e.id, version=e.version, snapshot=old))
    for k, v in new.items():
        setattr(e, k, v)
    e.version += 1
    e.division.spec_version += 1  # marks dependent assessments/plans stale
    comp.last_checked_at = now()
    db.commit()
    return d(e)


# ---------------------------------------------------------------- assessments
def _stale(a: Assessment, db: Session) -> tuple[bool, list[str]]:
    div = db.get(CompetitionDivision, a.division_id)
    comp = db.get(Competition, a.competition_id)
    reasons = []
    if div.spec_version != a.division_spec_version:
        reasons.append("The competition's event requirements changed after this report was made.")
    if comp.status != a.competition_status:
        reasons.append(f"The competition status changed from {a.competition_status} to {comp.status}.")
    return bool(reasons), reasons


def _assessment_out(a: Assessment, db: Session) -> dict:
    stale, reasons = _stale(a, db)
    out = d(a)
    out["stale"], out["stale_reasons"] = stale, reasons
    return out


def _own_assessment(db, owner, aid) -> Assessment:
    a = db.get(Assessment, aid)
    if not a or a.owner_id != owner:
        raise HTTPException(404, "Assessment not found.")
    return a


@router.post("/assessments", status_code=201)
def create_assessment(body: AssessmentIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    comp = _visible_competition(db, owner, body.competition_id)
    div = db.get(CompetitionDivision, body.division_id)
    if not div or div.competition_id != comp.id:
        raise HTTPException(404, "Division not found in that competition.")
    profile = _profile(db, owner)
    equipment = db.query(EquipmentAccess).filter_by(owner_id=owner).all()
    records = db.query(PerformanceRecord).filter_by(owner_id=owner).all()
    history = db.query(HistoricalResult).all()
    result = assess_svc.build_assessment(profile, equipment, records, comp, div, history)
    snap = jsonable_encoder({"profile": d(profile) if profile else None, "equipment": [d(e) for e in equipment],
                             "record_ids": [r.id for r in records]})
    a = Assessment(owner_id=owner, competition_id=comp.id, division_id=div.id, division_spec_version=div.spec_version,
                   competition_status=comp.status, calculation_version=result["calculation_version"],
                   profile_snapshot=snap, result=result)
    db.add(a)
    db.commit()
    return _assessment_out(a, db)


@router.get("/assessments")
def list_assessments(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    rows = db.query(Assessment).filter_by(owner_id=owner).order_by(Assessment.id.desc()).all()
    return [{**{k: v for k, v in _assessment_out(a, db).items() if k not in ("result", "profile_snapshot")},
             "summary_counts": a.result["summary_counts"], "competition_title": a.result["competition"]["title"],
             "division_name": a.result["division"]["name"]} for a in rows]


@router.get("/assessments/{aid}")
def get_assessment(aid: int, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return _assessment_out(_own_assessment(db, owner, aid), db)


# ---------------------------------------------------------------- plans
def _plan_out(p: PreparationPlan, db: Session) -> dict:
    a = db.get(Assessment, p.assessment_id)
    stale, reasons = _stale(a, db)
    out = d(p)
    out["stale"], out["stale_reasons"] = stale, reasons
    out["competition_title"] = a.result["competition"]["title"]
    return out


def _own_plan(db, owner, pid) -> PreparationPlan:
    p = db.get(PreparationPlan, pid)
    if not p or p.owner_id != owner:
        raise HTTPException(404, "Plan not found.")
    return p


@router.post("/preparation-plans", status_code=201)
def create_plan(body: PlanIn, owner: str = Depends(current_owner), db: Session = Depends(get_db),
                settings: Settings = Depends(get_settings)):
    a = _own_assessment(db, owner, body.assessment_id)
    stale, reasons = _stale(a, db)
    if stale:
        raise HTTPException(409, detail={"message": "This assessment is stale; run a new assessment first.", "errors": reasons})
    comp = db.get(Competition, a.competition_id)
    profile = _profile(db, owner)
    equipment = db.query(EquipmentAccess).filter_by(owner_id=owner).all()
    templates = db.query(ExerciseTemplate).all()
    try:
        ctx = planning.build_context(profile, equipment, templates, a.result, comp, date.today())
        plan, provider = planning.generate_validated_plan(ctx, settings)
    except planning.PlanError as exc:
        raise HTTPException(exc.status, detail={"message": str(exc), "errors": exc.errors})
    used = {x["key"]: x["template_version"] for x in ctx["templates"]}
    version = db.query(PreparationPlan).filter_by(owner_id=owner, assessment_id=a.id).count() + 1
    p = PreparationPlan(owner_id=owner, assessment_id=a.id, version=version, provider=provider,
                        template_versions=sorted({f"{k}@{v}" for k, v in used.items()}), content=plan, review_state="draft")
    db.add(p)
    db.commit()
    return _plan_out(p, db)


@router.get("/preparation-plans")
def list_plans(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return [{k: v for k, v in _plan_out(p, db).items() if k != "content"} for p in
            db.query(PreparationPlan).filter_by(owner_id=owner).order_by(PreparationPlan.id.desc())]


@router.get("/preparation-plans/{pid}")
def get_plan(pid: int, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return _plan_out(_own_plan(db, owner, pid), db)


@router.post("/preparation-plans/{pid}/save")
def save_plan(pid: int, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    p = _own_plan(db, owner, pid)
    out = _plan_out(p, db)
    if out["stale"]:
        raise HTTPException(409, detail={"message": "Stale plans cannot be saved; reassess and regenerate.", "errors": out["stale_reasons"]})
    p.review_state, p.saved_at = "saved", now()
    db.commit()
    return _plan_out(p, db)


# ---------------------------------------------------------------- training
@router.post("/training-logs", status_code=201)
def add_log(body: TrainingLogIn, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    if body.plan_id is not None:
        _own_plan(db, owner, body.plan_id)
    log = TrainingLog(owner_id=owner, plan_id=body.plan_id, planned_session=body.planned_session,
                      session_date=body.session_date, completed=body.completed,
                      exercises=[x.model_dump() for x in body.exercises], effort_rpe=body.effort_rpe, notes=body.notes)
    db.add(log)
    db.flush()
    for perf in body.new_performance:
        db.add(PerformanceRecord(owner_id=owner, training_log_id=log.id, **perf.model_dump()))
    db.commit()
    return d(log)


@router.get("/training-logs")
def list_logs(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    return [d(x) for x in db.query(TrainingLog).filter_by(owner_id=owner).order_by(TrainingLog.session_date.desc(), TrainingLog.id.desc())]


@router.delete("/training-logs/{lid}", status_code=204)
def delete_log(lid: int, owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    x = db.get(TrainingLog, lid)
    if not x or x.owner_id != owner:
        raise HTTPException(404, "Log not found.")
    db.query(PerformanceRecord).filter_by(training_log_id=lid).delete()
    db.delete(x)
    db.commit()


# ---------------------------------------------------------------- dashboard / export / delete
@router.get("/dashboard")
def dashboard(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    p = _profile(db, owner)
    out = {"completeness": _completeness(db, owner, p), "target": None, "assessment": None, "plan": None,
           "recent_logs": [d(x) for x in db.query(TrainingLog).filter_by(owner_id=owner).order_by(TrainingLog.session_date.desc(), TrainingLog.id.desc()).limit(5)]}
    if p and p.target_division_id:
        comp, div = db.get(Competition, p.target_competition_id), db.get(CompetitionDivision, p.target_division_id)
        out["target"] = {"competition_id": comp.id, "title": comp.title, "date": comp.start_date, "status": comp.status,
                         "division_id": div.id, "division_name": div.name, "days_left": (comp.start_date - date.today()).days,
                         "is_demo": comp.is_demo}
        a = db.query(Assessment).filter_by(owner_id=owner, division_id=div.id).order_by(Assessment.id.desc()).first()
        if a:
            ao = _assessment_out(a, db)
            out["assessment"] = {"id": a.id, "stale": ao["stale"], "stale_reasons": ao["stale_reasons"], "created_at": a.created_at,
                                 "summary_counts": a.result["summary_counts"], "eligibility": a.result["eligibility"]["status"],
                                 "top_priorities": [{"event": e["event_name"], "status_label": e["status_label"]}
                                                    for e in sorted(a.result["events"], key=lambda e: e["priority"])[:3]
                                                    if e["status"] != "demonstrated"]}
            plan = (db.query(PreparationPlan).filter_by(owner_id=owner, assessment_id=a.id)
                    .order_by((PreparationPlan.review_state == "saved").desc(), PreparationPlan.id.desc()).first())
            if plan:
                po = _plan_out(plan, db)
                out["plan"] = {k: po[k] for k in ("id", "version", "review_state", "provider", "stale", "created_at")}
    return out


@router.get("/export")
def export_data(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    p = _profile(db, owner)
    return {
        "profile": d(p) if p else None,
        "equipment": get_equipment(owner, db), "performance_records": list_records(owner, db),
        "assessments": [d(a) for a in db.query(Assessment).filter_by(owner_id=owner)],
        "plans": [d(x) for x in db.query(PreparationPlan).filter_by(owner_id=owner)],
        "training_logs": list_logs(owner, db),
        "private_competitions": [d(c) for c in db.query(Competition).filter_by(owner_id=owner)],
    }


@router.delete("/my-data", status_code=204)
def delete_my_data(owner: str = Depends(current_owner), db: Session = Depends(get_db)):
    db.query(PerformanceRecord).filter_by(owner_id=owner).delete()
    db.query(TrainingLog).filter_by(owner_id=owner).delete()
    db.query(PreparationPlan).filter_by(owner_id=owner).delete()
    db.query(Assessment).filter_by(owner_id=owner).delete()
    db.query(EquipmentAccess).filter_by(owner_id=owner).delete()
    db.query(AthleteProfile).filter_by(owner_id=owner).delete()
    for c in db.query(Competition).filter_by(owner_id=owner).all():
        for v in c.divisions:
            for e in v.events:
                db.query(SourceEvidence).filter_by(entity_type="event", entity_id=e.id).delete()
                db.query(EventSpecRevision).filter_by(event_id=e.id).delete()
        db.query(SourceEvidence).filter_by(entity_type="competition", entity_id=c.id).delete()
        db.delete(c)
    db.commit()
