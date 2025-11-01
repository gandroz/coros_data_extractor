"""Pydantic models for COROS Training Hub activity data.

This module provides a set of Pydantic models that represent COROS activity data:
    - Summary: Activity overview (time, distance, heart rate, etc.)
    - Frequencies: Time series data collected during an activity
    - Lap: Individual lap metrics for activities with lap data
    - TrainActivity: Complete activity with summary, time series, and laps
    - TrainActivities: Container for multiple activities

The models handle timestamp conversion (COROS timestamps to datetime objects) and
proper serialization for JSON export.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, RootModel, field_serializer, field_validator


class Summary(BaseModel):
    """Activity summary data including metrics and timestamps.

    Attributes:
        adjustedPace (int): Pace adjusted for elevation/terrain
        aerobicEffect (float): Training effect on aerobic fitness (0.0-5.0)
        aerobicEffectState (int): Current aerobic training state
        anaerobicEffect (float): Training effect on anaerobic fitness (0.0-5.0)
        anaerobicEffectState (int): Current anaerobic training state
        avgCadence (int): Average steps per minute
        avgHr (int): Average heart rate in BPM
        avgMoveSpeed (int): Average moving speed
        avgPace (int): Average pace
        avgRunningEf (int): Average running efficiency
        avgSpeed (float): Average speed including stops
        avgStepLen (int): Average step length in cm
        calories (int): Estimated calories burned
        currentVo2Max (int): Estimated VO2 max
        deviceSportMode (int): Sport mode set on device
        distance (int): Total distance in meters
        endTimestamp (datetime): Activity end time (timezone-aware)
        maxCadence (int): Maximum cadence reached
        maxHr (int): Maximum heart rate reached
        maxSpeed (int): Maximum speed achieved
        name (str): Activity name
        sportMode (int): Sport mode identifier
        sportType (int): Type of sport/activity
        startTimestamp (datetime): Activity start time (timezone-aware)
        totalTime (int): Total time including stops in seconds
        trainType (int): Training type identifier
        trainingLoad (int): Training load score
        workoutTime (int): Active workout time in seconds

    Note:
        Timestamps are converted from COROS format (1/100th second since epoch)
        to timezone-aware datetime objects.
    """

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
        """Convert COROS timestamp to timezone-aware datetime.

        Args:
            value: COROS timestamp (1/100th second since epoch)

        Returns:
            datetime: Timezone-aware datetime object

        Note:
            COROS timestamps are in 1/100th of a second since Unix epoch.
            They are converted to UTC then localized to the system timezone.
        """
        return (datetime.fromtimestamp(0, UTC) + timedelta(seconds=value / 100)).astimezone()

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info) -> date:
        """Convert datetime to ISO-8601 string for JSON export.

        Args:
            dt: Datetime object to serialize
            _info: Serialization context (unused)

        Returns:
            str: ISO-8601 formatted datetime string
        """
        return dt.isoformat()


class Frequencies(BaseModel):
    """Time series data collected during an activity.

    Each list represents a metric tracked over time, with values synchronized
    to the timestamps list.

    Attributes:
        cadence (list[int]): Steps per minute at each time point
        distance (list[int]): Cumulative distance in meters
        heart (list[int]): Heart rate in BPM
        heartLevel (list[int]): Heart rate zone (0-5)
        timestamp (list[int]): Time points in activity (COROS format)

    Note:
        All lists have the same length, with values at index i corresponding
        to the same moment in time (timestamp[i]).
    """

    cadence: list[int] = []
    distance: list[int] = []
    heart: list[int] = []
    heartLevel: list[int] = []
    timestamp: list[int] = []


class Lap(BaseModel):
    """Individual lap data for activities with lap tracking.

    Attributes:
        avgCadence (int): Average steps per minute for this lap
        avgHr (int): Average heart rate in BPM
        avgMoveSpeed (int): Average moving speed (excludes stops)
        avgPace (float): Average pace per kilometer/mile
        avgPower (int): Average power output in watts
        avgSpeedV2 (float): Refined average speed calculation
        avgStrideLength (int): Average stride length in cm
        calories (int): Estimated calories burned in this lap
        distance (int): Lap distance in meters
        endTimestamp (datetime): Lap end time (timezone-aware)
        lapIndex (int): Sequential number of this lap
        rowIndex (int): Internal row reference
        setIndex (int): Set number for multi-set activities
        startTimestamp (datetime): Lap start time (timezone-aware)
        totalDistance (int): Cumulative distance at lap end

    Note:
        Timestamps are converted from COROS format (1/100th second since epoch)
        to timezone-aware datetime objects.
    """

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
        return (datetime.fromtimestamp(0, UTC) + timedelta(seconds=value / 100)).astimezone()

    @field_serializer("startTimestamp", "endTimestamp")
    def serialize_dt(self, dt: datetime, _info) -> date:
        """Serialize datetime to ISO-8601 format."""
        return dt.isoformat()


class TrainActivity(BaseModel):
    """Complete activity record including summary, time series, and lap data.

    Attributes:
        summary (Summary): Overall activity metrics and metadata
        data (Frequencies): Time series data collected during activity
        laps (list[Lap]): List of lap records if available

    Example:
        >>> activity = TrainActivity(
        ...     summary=activity_summary,  # From API response
        ...     data=activity_frequencies,  # From API response
        ...     laps=activity_laps  # From API response
        ... )
        >>> print(f"Activity: {activity.summary.name}")
        >>> print(f"Duration: {activity.summary.workoutTime}s")
    """

    summary: Summary
    data: Frequencies
    laps: list[Lap]


class TrainActivities(RootModel):
    """Container for multiple training activities with list-like behavior.

    A collection of TrainActivity objects that can be iterated over, indexed,
    and extended. Used as the root model for JSON export/import.

    Attributes:
        root (list[TrainActivity]): List of training activities

    Example:
        >>> activities = TrainActivities()
        >>> activities.add_activity(new_activity)
        >>> for activity in activities:
        ...     print(activity.summary.name)
        >>> latest = activities[-1]  # Get most recent activity
    """

    root: list[TrainActivity] = []

    def __iter__(self):
        """Enable iteration over activities.

        Returns:
            Iterator[TrainActivity]: Iterator over the activities list.
        """
        return iter(self.root)

    def __getitem__(self, item):
        """Access activities by index.

        Args:
            item (int): Index of the activity to retrieve.

        Returns:
            TrainActivity: The activity at the specified index.

        Raises:
            IndexError: If the index is out of range.
        """
        return self.root[item]

    def add_activity(self, activity: TrainActivity):
        """Add a new activity to the collection.

        Args:
            activity (TrainActivity): The activity to add to the collection.
        """
        self.root.append(activity)
