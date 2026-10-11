"""Per-field source evidence and review-status roll-ups for competitions."""
from sqlalchemy.orm import Session

from app.models import Competition, SourceEvidence

REVIEW_STATUSES = ("unverified", "confirmed", "conflicting")


def event_fields(ev) -> list[str]:
    """Which event fields carry a published value that evidence should cover."""
    fields = ["scoring_type"]
    if ev.load_kg is not None:
        fields.append("load_kg")
    if getattr(ev, "load_per_hand", False):
        fields.append("load_per_hand")
    if ev.time_limit_s is not None:
        fields.append("time_limit_s")
    if ev.distance_m is not None:
        fields.append("distance_m")
    return fields


def division_fields(div) -> list[str]:
    fields = []
    if div.weight_min_kg is not None or div.weight_max_kg is not None:
        fields.append("weight_range")
    if div.age_min is not None or div.age_max is not None:
        fields.append("age_range")
    if div.eligibility_notes:
        fields.append("eligibility_notes")
    return fields


def ensure_evidence(db: Session, entity_type: str, entity_id: int, field: str, *, url, retrieved_at, excerpt, review_status) -> bool:
    """Add one evidence row unless that (entity, field) already has one. Returns True if added."""
    exists = db.query(SourceEvidence).filter_by(entity_type=entity_type, entity_id=entity_id, field_name=field).first()
    if exists:
        return False
    db.add(SourceEvidence(entity_type=entity_type, entity_id=entity_id, field_name=field, url=url, retrieved_at=retrieved_at,
                          excerpt=excerpt, review_status=review_status))
    return True


def _rollup(statuses: list[str], fallback: str) -> str:
    if not statuses:
        return fallback
    if "conflicting" in statuses:
        return "conflicting"
    if all(s == "confirmed" for s in statuses):
        return "verified"
    return "unverified"


def recompute_verification(db: Session, comp: Competition) -> None:
    """conflicting beats everything; verified only when ALL evidence is confirmed; otherwise unverified."""
    all_statuses: list[str] = []
    for div in comp.divisions:
        rows = db.query(SourceEvidence).filter_by(entity_type="division", entity_id=div.id).all()
        all_statuses += [r.review_status for r in rows]
        for ev in div.events:
            rows = db.query(SourceEvidence).filter_by(entity_type="event", entity_id=ev.id).all()
            statuses = [r.review_status for r in rows]
            all_statuses += statuses
            if statuses:
                ev.verification_status = _rollup(statuses, ev.verification_status)
    all_statuses += [r.review_status for r in db.query(SourceEvidence).filter_by(entity_type="competition", entity_id=comp.id)]
    comp.verification_status = _rollup(all_statuses, comp.verification_status)
