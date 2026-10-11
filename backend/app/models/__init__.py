from datetime import date, datetime, time, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    body_weight_kg: Mapped[float | None] = mapped_column(Float)
    age: Mapped[int | None] = mapped_column(Integer)
    division_category: Mapped[str | None] = mapped_column(String(40))  # men | women | open
    experience_level: Mapped[str | None] = mapped_column(String(20))  # novice | intermediate
    competitions_entered: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(120))
    travel_radius_km: Mapped[int | None] = mapped_column(Integer)
    approx_lat: Mapped[float | None] = mapped_column(Float)  # rounded to 2 decimals; never an exact address
    approx_lon: Mapped[float | None] = mapped_column(Float)
    days_per_week: Mapped[int | None] = mapped_column(Integer)
    session_minutes: Mapped[int | None] = mapped_column(Integer)
    other_commitments: Mapped[str | None] = mapped_column(Text)
    avoid_exercises: Mapped[list] = mapped_column(JSON, default=list)  # template/task keys
    pain_flags: Mapped[list] = mapped_column(JSON, default=list)  # body-area tags
    goal: Mapped[str | None] = mapped_column(String(40))  # participate | perform
    target_competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"))
    target_division_id: Mapped[int | None] = mapped_column(ForeignKey("competition_divisions.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EquipmentAccess(Base):
    __tablename__ = "equipment_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    implement: Mapped[str] = mapped_column(String(40))
    access: Mapped[str] = mapped_column(String(12))  # regular | occasional | none
    max_load_kg: Mapped[float | None] = mapped_column(Float)
    # True when max_load_kg is for ONE hand/handle (e.g. "50 kg dumbbells"); False when it is the total load
    limit_is_per_hand: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa_false())
    carry_space_m: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(String(300))


class PerformanceRecord(Base):
    __tablename__ = "performance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    task_key: Mapped[str] = mapped_column(String(40))
    load_kg: Mapped[float | None] = mapped_column(Float)
    load_per_hand: Mapped[bool] = mapped_column(Boolean, default=False)
    reps: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[float | None] = mapped_column(Float)
    time_s: Mapped[float | None] = mapped_column(Float)
    record_date: Mapped[date] = mapped_column(Date)
    effort_rpe: Mapped[float | None] = mapped_column(Float)
    conditions: Mapped[str | None] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(20), default="self_reported")
    # self_reported | verified_training | official_result
    training_log_id: Mapped[int | None] = mapped_column(ForeignKey("training_logs.id"))


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), index=True)  # null = shared catalog
    title: Mapped[str] = mapped_column(String(200))
    organizer: Mapped[str | None] = mapped_column(String(200))
    federation: Mapped[str | None] = mapped_column(String(120))
    venue: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)  # approximate venue location
    longitude: Mapped[float | None] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time | None] = mapped_column(Time)  # venue-local wall-clock time; None = not published
    timezone: Mapped[str | None] = mapped_column(String(64))  # IANA name, e.g. Asia/Manila
    registration_deadline: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    registration_url: Mapped[str | None] = mapped_column(String(500))
    entry_fee: Mapped[float | None] = mapped_column(Float)
    fee_currency: Mapped[str | None] = mapped_column(String(8))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="upcoming")  # upcoming|canceled|completed
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    demo_label: Mapped[str | None] = mapped_column(String(200))

    divisions: Mapped[list["CompetitionDivision"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan", order_by="CompetitionDivision.id"
    )


class CompetitionDivision(Base):
    __tablename__ = "competition_divisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))  # men | women | open
    weight_min_kg: Mapped[float | None] = mapped_column(Float)
    weight_max_kg: Mapped[float | None] = mapped_column(Float)
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    eligibility_notes: Mapped[str | None] = mapped_column(Text)
    needs_manual_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    spec_version: Mapped[int] = mapped_column(Integer, default=1)

    competition: Mapped[Competition] = relationship(back_populates="divisions")
    events: Mapped[list["EventSpecification"]] = relationship(
        back_populates="division", cascade="all, delete-orphan", order_by="EventSpecification.position"
    )


class EventSpecification(Base):
    __tablename__ = "event_specifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int] = mapped_column(ForeignKey("competition_divisions.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200))
    task_key: Mapped[str] = mapped_column(String(40))
    scoring_type: Mapped[str] = mapped_column(String(20))  # max_load|reps|time|distance|custom
    load_kg: Mapped[float | None] = mapped_column(Float)
    load_per_hand: Mapped[bool] = mapped_column(Boolean, default=False)
    original_load_text: Mapped[str | None] = mapped_column(String(120))
    original_unit: Mapped[str | None] = mapped_column(String(8))  # kg | lb | unknown
    time_limit_s: Mapped[float | None] = mapped_column(Float)
    distance_m: Mapped[float | None] = mapped_column(Float)
    rules_text: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    version: Mapped[int] = mapped_column(Integer, default=1)

    division: Mapped[CompetitionDivision] = relationship(back_populates="events")


class EventSpecRevision(Base):
    """Prior versions of an event specification, kept when requirements change."""

    __tablename__ = "event_spec_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("event_specifications.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    superseded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceEvidence(Base):
    __tablename__ = "source_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # competition | division | event
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    field_name: Mapped[str] = mapped_column(String(60))
    url: Mapped[str | None] = mapped_column(String(500))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excerpt: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(20), default="fixture")


class HistoricalResult(Base):
    __tablename__ = "historical_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_key: Mapped[str] = mapped_column(String(40), index=True)
    scoring_type: Mapped[str] = mapped_column(String(20))
    division_category: Mapped[str] = mapped_column(String(40))
    performance_category: Mapped[str] = mapped_column(String(20), default="novice")
    load_kg: Mapped[float | None] = mapped_column(Float)
    load_per_hand: Mapped[bool] = mapped_column(Boolean, default=False)
    time_limit_s: Mapped[float | None] = mapped_column(Float)
    distance_m: Mapped[float | None] = mapped_column(Float)
    athlete_key: Mapped[str] = mapped_column(String(60))
    competition_name: Mapped[str] = mapped_column(String(200))
    result_date: Mapped[date] = mapped_column(Date)
    result_value: Mapped[float] = mapped_column(Float)  # kg | reps | seconds | metres
    provenance: Mapped[str] = mapped_column(String(300))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class ExerciseTemplate(Base):
    __tablename__ = "exercise_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(30))  # strength | event_practice | conditioning | accessory
    equipment: Mapped[list] = mapped_column(JSON, default=list)  # all required implements
    demand_tags: Mapped[list] = mapped_column(JSON, default=list)  # event families supported
    body_areas: Mapped[list] = mapped_column(JSON, default=list)  # tags for pain-flag exclusion
    task_key: Mapped[str | None] = mapped_column(String(40))  # set for event-specific practice
    sets: Mapped[int] = mapped_column(Integer, default=3)
    reps: Mapped[str] = mapped_column(String(20), default="5")
    intensity: Mapped[str] = mapped_column(String(60), default="RPE 6-7")
    limitation: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(20), default="unreviewed_demo")
    template_version: Mapped[str] = mapped_column(String(20), default="demo-0.1")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"))
    division_id: Mapped[int] = mapped_column(ForeignKey("competition_divisions.id"))
    division_spec_version: Mapped[int] = mapped_column(Integer)
    competition_status: Mapped[str] = mapped_column(String(20))
    calculation_version: Mapped[str] = mapped_column(String(30))
    evidence_hash: Mapped[str | None] = mapped_column(String(64))  # None = report predates fingerprints
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PreparationPlan(Base):
    __tablename__ = "preparation_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(20))  # mock | claude
    template_versions: Mapped[list] = mapped_column(JSON, default=list)
    inputs_hash: Mapped[str | None] = mapped_column(String(64))  # None = plan predates fingerprints
    content: Mapped[dict] = mapped_column(JSON)
    review_state: Mapped[str] = mapped_column(String(12), default="draft")  # draft | saved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrainingLog(Base):
    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("preparation_plans.id"))
    planned_session: Mapped[str | None] = mapped_column(String(60))  # e.g. "week 2 / session 1"
    session_date: Mapped[date] = mapped_column(Date)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    exercises: Mapped[list] = mapped_column(JSON, default=list)
    effort_rpe: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AiSetting(Base):
    """Per-owner AI provider settings entered in the app. The API key is stored encrypted and never returned."""

    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(24))  # mock | claude | openai_compatible
    base_url: Mapped[str | None] = mapped_column(String(300))
    model: Mapped[str | None] = mapped_column(String(120))
    encrypted_key: Mapped[str | None] = mapped_column(Text)
    key_last4: Mapped[str | None] = mapped_column(String(4))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
