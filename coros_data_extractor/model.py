from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, RootModel
from datetime import datetime, timedelta, timezone
from typing import Any, List
import pytz


class Summary(BaseModel):
    """Model with summary ata of an activity"""
    model_config = ConfigDict(extra='ignore')

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
        return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=value / 100)).astimezone(pytz.timezone("America/New_York"))
    
    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()


class Frequencies(BaseModel):
    """Time series model of the collected data during an activity"""
    model_config = ConfigDict(extra='ignore')

    cadence: List[int] = []
    distance: List[int] = []
    heart: List[int] = []
    heartLevel: List[int] = []
    timestamp: List[int] = []


class Lap(BaseModel):
    """Lap data model"""
    model_config = ConfigDict(extra='ignore')

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
        return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=value / 100)).astimezone(pytz.timezone("America/New_York"))
    
    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()


class TrainActivity(BaseModel):
    """Activity model"""
    model_config = ConfigDict(extra='ignore')
    
    summary: Summary
    data: Frequencies
    laps: list[Lap]


class TrainActivities(RootModel):
    """List of activities model"""
    root: list[TrainActivity] = []

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]
    
    def add_activity(self, activity: TrainActivity):
        self.root.append(activity)
