"""Data models for the Coros data extractor."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel, field_serializer, field_validator


class Summary(BaseModel):
    """Model representing the summary for an activity."""

    adjustedPace: int
    aerobicEffect: float
    aerobicEffectState: int
    anaerobicEffect: float
    anaerobicEffectState: int
    avgCadence: int
    avgHr: int
    avgMoveSpeed: int
    avgPace: int
    avgRunningEf: int
    avgSpeed: float
    avgStepLen: int
    calories: int
    currentVo2Max: int
    deviceSportMode: int
    distance: int
    endTimestamp: datetime
    maxCadence: int
    maxHr: int
    maxSpeed: int
    name: str
    sportMode: int
    sportType: int
    startTimestamp: datetime
    totalTime: int
    trainType: int
    trainingLoad: int
    workoutTime: int

    @field_validator("startTimestamp", "endTimestamp", mode="before")
    @classmethod
    def convert_timestamp_to_datetime(cls, value: Any) -> datetime:
        """Convert timestamp to datetime."""
        return (
            datetime.fromtimestamp(0, timezone.utc) + timedelta(seconds=value / 100)
        ).astimezone()

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info) -> date:
        """Serialize datetime to ISO-8601 format."""
        return dt.isoformat()


class Frequencies(BaseModel):
    """Time series model of the collected data during an activity."""

    cadence: list[int] = []
    distance: list[int] = []
    heart: list[int] = []
    heartLevel: list[int] = []
    timestamp: list[int] = []


class Lap(BaseModel):
    """Lap data model."""

    avgCadence: int
    avgHr: int
    avgMoveSpeed: int
    avgPace: float
    avgPower: int
    avgSpeedV2: float
    avgStrideLength: int
    calories: int
    distance: int
    endTimestamp: datetime
    lapIndex: int
    rowIndex: int
    setIndex: int
    startTimestamp: datetime
    totalDistance: int

    @field_validator("startTimestamp", "endTimestamp", mode="before")
    @classmethod
    def convert_timestamp_to_datetime(cls, value: Any) -> datetime:
        """Convert timestamp to datetime."""
        return (
            datetime.fromtimestamp(0, timezone.utc) + timedelta(seconds=value / 100)
        ).astimezone()

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info) -> date:
        """Serialize datetime to ISO-8601 format."""
        return dt.isoformat()


class TrainActivity(BaseModel):
    """Activity model."""

    summary: Summary
    data: Frequencies
    laps: list[Lap]


class TrainActivities(RootModel):
    """List of activities model."""

    root: list[TrainActivity] = []

    def __iter__(self):
        """Iterate over activities."""
        return iter(self.root)

    def __getitem__(self, item):
        """Get activity by index."""
        return self.root[item]

    def add_activity(self, activity: TrainActivity):
        """Add an activity to the list."""
        self.root.append(activity)
