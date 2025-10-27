"""Data models for the Coros data extractor."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytz
from pydantic import BaseModel, ConfigDict, RootModel, field_serializer, field_validator


class Summary(BaseModel):
    """Model with summary ata of an activity."""

    model_config = ConfigDict(extra="ignore")

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
    def convert_timestamp_to_datetime(cls, value: Any) -> Any:
        """Convert timestamp to datetime."""
        return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=value / 100)).astimezone(
            pytz.timezone("America/New_York")
        )

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info):
        """Serialize datetime to iso format."""
        return dt.isoformat()


class Frequencies(BaseModel):
    """Time series model of the collected data during an activity."""

    model_config = ConfigDict(extra="ignore")

    cadence: list[int] = []
    distance: list[int] = []
    heart: list[int] = []
    heartLevel: list[int] = []
    timestamp: list[int] = []


class Lap(BaseModel):
    """Lap data model."""

    model_config = ConfigDict(extra="ignore")

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
    def convert_timestamp_to_datetime(cls, value: Any) -> Any:
        """Convert timestamp to datetime."""
        return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=value / 100)).astimezone(
            pytz.timezone("America/New_York")
        )

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info):
        """Serialize datetime to iso format."""
        return dt.isoformat()


class TrainActivity(BaseModel):
    """Activity model."""

    model_config = ConfigDict(extra="ignore")

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
