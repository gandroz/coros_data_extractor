"""Coros data extractor from Training Hub."""

import hashlib
import json
from pathlib import Path

import requests

from coros_data_extractor.model import (
    Frequencies,
    Lap,
    Summary,
    TrainActivities,
    TrainActivity,
)

base_url = "https://teamapi.coros.com/"
login_url = base_url + "account/login"
activities_url = base_url + "activity/query"
activity_details_url = base_url + "activity/detail/query"


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
        resp = requests.post(login_url, json=request_data)
        self.access_token = resp.json()["data"]["accessToken"]

    def get_activities(self) -> dict:
        """Extract list of activities from API."""
        payload = {
            "size": 200,
            "pageNumber": 1,
            "modeList": "",
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
        resp = requests.post(activity_details_url, headers=headers, params=payload)
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
            if item["type"] == 2:
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
