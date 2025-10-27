"""Coros data extractor from Training Hub."""

import hashlib
import json
from enum import Enum
from pathlib import Path

import requests

from .config import (
    ACTIVITIES_URL,
    ACTIVITY_DETAILS_URL,
    LOGIN_URL,
)
from .model import (
    Frequencies,
    Lap,
    Summary,
    TrainActivities,
    TrainActivity,
)


class ActivityType(Enum):
    INDOOR_RUN = 101
    HIKE = 104
    INDOOR_BIKE = 201
    SKI_TOURING = 503
    INDOOR_CLIMB = 800
    BOULDERING = 801
    WALK = 900
    JUMP_ROPE = 901
    MULTISPORT = 10001


class LapType(Enum):
    BIKE_RIDE = 1
    RUNNING = 2


class CorosDataExtractor:
    """Coros data extractor from Training Hub."""

    def __init__(self) -> None:
        """Initialize extractor."""
        self.activities = None
        self.access_token = None

    def login(self, email: str, pwd: str) -> None:
        """Login to Coros API."""
        request_data = {
            "account": email,
            "accountType": 2,
            "pwd": hashlib.md5(pwd.encode()).hexdigest(),
        }
        resp = requests.post(LOGIN_URL, json=request_data)
        self.access_token = resp.json()["data"]["accessToken"]

    def get_activities(
        self,
        activity_types: list[int] | None = None,
    ) -> dict:
        """Extract list of activities from API."""

        if activity_types is None:
            mode_list = ""
        else:
            mode_list = ",".join(str(activity_type) for activity_type in activity_types)

        payload = {
            "size": 200,
            "modeList": mode_list,
            "pageNumber": 1,
        }
        headers = {"Accesstoken": self.access_token}
        resp = requests.get(activities_url, headers=headers, params=payload)
        res = resp.json()
        return res["data"]["dataList"]

    def get_activity_raw_data(self, activity) -> dict:
        """Extract raw data of one activity."""
        payload = {
            "labelId": activity["labelId"],
            "sportType": activity["sportType"],
            "screenW": 944,
            "screenH": 1440,
        }
        headers = {"Accesstoken": self.access_token}
        resp = requests.post(ACTIVITY_DETAILS_URL, headers=headers, params=payload)
        return resp.json()

    @staticmethod
    def get_activity_data(data) -> Frequencies:
        """Convert raw activity data to time series."""
        freq = Frequencies()
        for item in data:
            freq.cadence.append(item["cadence"] if "cadence" in item else 0)
            freq.distance.append(item["distance"] if "distance" in item else 0)
            freq.heart.append(item["heart"] if "heart" in item else 0)
            freq.heartLevel.append(item["heartLevel"] if "heartLevel" in item else 0)
            freq.timestamp.append(item["timestamp"] if "timestamp" in item else 0)
        return freq

    @staticmethod
    def get_summary_data(data) -> Summary:
        """Concert raw activity summary data to summary model."""
        return Summary(**data)

    @staticmethod
    def get_laps_data(data) -> list[Lap]:
        """Convert raw activity to laps data."""
        laps = []
        for item in data:
            if item["type"] == LapType.RUNNING:
                for lap in item["lapItemList"]:
                    laps.append(Lap(**lap))
        return laps

    def extract_data(self) -> None:
        """Extract data from Coros API and build data models accordingly."""
        # get all activites
        activities = self.get_activities()
        self.activities = TrainActivities()

        for _activity in activities:
            # extract raw data of an activity
            activity_data = self.get_activity_raw_data(_activity)
            # build pydantic models
            activity = TrainActivity(
                summary=CorosDataExtractor.get_summary_data(activity_data["data"]["summary"]),
                data=CorosDataExtractor.get_activity_data(activity_data["data"]["frequencyList"]),
                laps=CorosDataExtractor.get_laps_data(activity_data["data"]["lapList"]),
            )
            self.activities.add_activity(activity)

    def to_json(self, filename: str = "activities.json"):
        """Export data to json file."""
        if self.activities is not None:
            with Path(filename).open("w") as f:
                json.dump(self.activities.model_dump(), f, indent=2)
