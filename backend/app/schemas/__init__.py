from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.reference import BODY_AREAS, TASKS

Category = Literal["men", "women", "open"]


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(None, max_length=120)
    body_weight_kg: float | None = Field(None, gt=30, lt=300)
    age: int | None = Field(None, ge=14, le=100)
    division_category: Category | None = None
    experience_level: Literal["novice", "intermediate"] | None = None
    competitions_entered: int | None = Field(None, ge=0, le=500)
    city: str | None = Field(None, max_length=120)
    travel_radius_km: int | None = Field(None, ge=0, le=20000)
    days_per_week: int | None = Field(None, ge=1, le=7)
    session_minutes: int | None = Field(None, ge=15, le=240)
    other_commitments: str | None = Field(None, max_length=1000)
    avoid_exercises: list[str] = []
    pain_flags: list[str] = []
    goal: Literal["participate", "perform"] | None = None

    @field_validator("pain_flags")
    @classmethod
    def _pain(cls, v):
        bad = [x for x in v if x not in BODY_AREAS]
        if bad:
            raise ValueError(f"unknown body areas: {bad}")
        return v


class TargetIn(BaseModel):
    competition_id: int
    division_id: int


class EquipmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    implement: str
    access: Literal["regular", "occasional", "none"]
    max_load_kg: float | None = Field(None, ge=0, le=1000)
    carry_space_m: float | None = Field(None, ge=0, le=1000)
    notes: str | None = Field(None, max_length=300)


class PerformanceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_key: str
    load_kg: float | None = Field(None, gt=0, le=1000)
    load_per_hand: bool = False
    reps: int | None = Field(None, ge=1, le=1000)
    distance_m: float | None = Field(None, gt=0, le=1000)
    time_s: float | None = Field(None, gt=0, le=36000)
    record_date: date
    effort_rpe: float | None = Field(None, ge=1, le=10)
    conditions: str | None = Field(None, max_length=300)
    source_type: Literal["self_reported", "verified_training", "official_result"] = "self_reported"

    @field_validator("task_key")
    @classmethod
    def _task(cls, v):
        if v not in TASKS:
            raise ValueError("unknown task")
        return v

    @field_validator("record_date")
    @classmethod
    def _not_future(cls, v):
        if v > date.today():
            raise ValueError("record date cannot be in the future")
        return v

    @model_validator(mode="after")
    def _has_measure(self):
        if self.load_kg is None and self.reps is None and self.distance_m is None and self.time_s is None:
            raise ValueError("enter at least one of load, reps, distance or time")
        return self


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    task_key: str
    scoring_type: Literal["max_load", "reps", "time", "distance", "custom"]
    load_kg: float | None = Field(None, gt=0, le=1000)
    load_per_hand: bool = False
    original_load_text: str | None = Field(None, max_length=120)
    original_unit: Literal["kg", "lb", "unknown"] | None = None
    time_limit_s: float | None = Field(None, gt=0, le=3600)
    distance_m: float | None = Field(None, gt=0, le=1000)
    rules_text: str | None = Field(None, max_length=3000)

    @field_validator("task_key")
    @classmethod
    def _task(cls, v):
        if v not in TASKS:
            raise ValueError("unknown task")
        return v


class DivisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    category: Category
    weight_min_kg: float | None = Field(None, ge=0)
    weight_max_kg: float | None = Field(None, ge=0)
    age_min: int | None = Field(None, ge=0)
    age_max: int | None = Field(None, ge=0)
    eligibility_notes: str | None = Field(None, max_length=2000)
    needs_manual_confirmation: bool = False
    events: list[EventIn] = []

    @model_validator(mode="after")
    def _ranges(self):
        if self.weight_min_kg is not None and self.weight_max_kg is not None and self.weight_min_kg > self.weight_max_kg:
            raise ValueError("weight_min_kg exceeds weight_max_kg")
        if self.age_min is not None and self.age_max is not None and self.age_min > self.age_max:
            raise ValueError("age_min exceeds age_max")
        return self


class CompetitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    organizer: str | None = None
    venue: str | None = None
    city: str | None = None
    country: str | None = None
    start_date: date
    registration_deadline: date | None = None
    source_url: str | None = Field(None, max_length=500)
    registration_url: str | None = Field(None, max_length=500)
    entry_fee: float | None = Field(None, ge=0)
    fee_currency: str | None = Field(None, max_length=8)
    divisions: list[DivisionIn] = Field(min_length=1)


class AssessmentIn(BaseModel):
    competition_id: int
    division_id: int


class PlanIn(BaseModel):
    assessment_id: int


class LoggedExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    sets: int | None = Field(None, ge=1, le=50)
    reps: int | None = Field(None, ge=1, le=1000)
    load_kg: float | None = Field(None, ge=0, le=1000)


class NewPerformance(PerformanceIn):
    pass


class TrainingLogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: int | None = None
    planned_session: str | None = Field(None, max_length=60)
    session_date: date
    completed: bool = True
    exercises: list[LoggedExercise] = []
    effort_rpe: float | None = Field(None, ge=1, le=10)
    notes: str | None = Field(None, max_length=2000)
    new_performance: list[NewPerformance] = []

    @field_validator("session_date")
    @classmethod
    def _not_future(cls, v):
        if v > date.today():
            raise ValueError("session date cannot be in the future")
        return v
