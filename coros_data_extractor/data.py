"""Coros data extractor from Training Hub."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from enum import Enum
from pathlib import Path

import requests

from .config import (
    ACTIVITIES_URL,
    ACTIVITY_DETAILS_URL,
    ACTIVITY_PAGINATION_LIMIT,
    DEFAULT_ACTIVITY_LIMIT,
    LOGIN_URL,
)
from .model import (
    Frequencies,
    Lap,
    Summary,
    TrainActivities,
    TrainActivity,
)

# ruff: noqa: S324


API_TIMEOUT = 10

logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s: %(levelname)s: %(asctime)s %(message)s",
)
LOGGER = logging.getLogger(__name__)


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

    def login(self, account: str, password: str) -> None:
        """Login to Coros API."""
        request_data = {
            "account": account,
            "accountType": 2,
            "pwd": hashlib.md5(password.encode()).hexdigest(),
        }
        resp = requests.post(LOGIN_URL, json=request_data, timeout=API_TIMEOUT)
        resp.raise_for_status()
        self.access_token = resp.json()["data"]["accessToken"]

    def get_activities(
        self,
        limit: int | None = DEFAULT_ACTIVITY_LIMIT,
        activity_types: list[int] | None = None,
    ) -> dict:
        """Extract list of activities from API."""
        with requests.Session() as session:
            return self._get_activities_inner(
                session, limit=limit, activity_types=activity_types,
            )

    def _get_activities_inner(
        self,
        session: requests.Session,
        limit: ...,
        activity_types: ...,
    ) -> dict:
        """Extract list of activities from API (inner)."""
        if activity_types is None:
            mode_list = ""
        else:
            mode_list = ",".join(str(activity_type) for activity_type in activity_types)

        payload = {
            "modeList": mode_list,
            "pageNumber": 1,
        }
        headers = {"Accesstoken": self.access_token}

        if limit is None:
            # Need to figure out how many total activities there are.
            #
            # Query for a single activity to get the total count back for a
            # given activity type. This allows you to pull the data in chunks.
            payload["size"] = 1
            resp = session.get(
                ACTIVITIES_URL, headers=headers, params=payload, timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            res = resp.json()

            limit = ACTIVITY_PAGINATION_LIMIT
            total_activities = res["data"]["count"]
        else:
            # This is technically incorrect, but whatever... it doesn't really cause
            # any grief AFAICT.
            total_activities = limit

        payload["size"] = min(limit, ACTIVITY_PAGINATION_LIMIT)

        datalist = []
        num_pages = math.ceil(total_activities / limit)
        for page_number in range(1, num_pages + 1):
            payload["pageNumber"] = page_number

            resp = session.get(
                ACTIVITIES_URL,
                headers=headers,
                params=payload,
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            res = resp.json()

            datalist.extend(res["data"]["dataList"])

        return datalist

    @staticmethod
    def valid_raw_activity_data(resp_json: dict) -> bool:
        return resp_json.get("data", {}).get("summary") is not None

    def get_raw_activity_data(
        self,
        session: requests.Session,
        activity: dict,
    ) -> dict:
        """Extract raw data of one activity."""
        MAX_TRIES = 3
        WAIT_BETWEEN_RETRIES = 0.5

        for retries_left in range(MAX_TRIES - 1, -1, -1):
            try:
                resp_json = self._get_raw_activity_data_inner(
                    session, activity,
                )
            except Exception:
                LOGGER.exception("An exception occurred when downloading the raw JSON")
            else:
                if self.valid_raw_activity_data(resp_json):
                    return resp_json

                LOGGER.error(
                    "JSON malformed or contained unexpected elements: %r",
                    resp_json,
                )

            if retries_left:
                LOGGER.warning("Will retry %d more times", retries_left)
                time.sleep(WAIT_BETWEEN_RETRIES)

        err_msg = (
            f"REST API call to {ACTIVITY_DETAILS_URL=} failed after {MAX_TRIES} "
            "attempts."
        )
        raise RuntimeError(err_msg)

    def _get_raw_activity_data_inner(
        self,
        session: requests.Session,
        activity: ...,
    ) -> dict:
        payload = {
            "labelId": activity["labelId"],
            "sportType": activity["sportType"],
            "screenW": 944,
            "screenH": 1440,
        }
        headers = {"Accesstoken": self.access_token}
        resp = session.post(
            ACTIVITY_DETAILS_URL, headers=headers, params=payload, timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def get_activity_data(data) -> Frequencies:
        """Convert raw activity data to time series."""
        freq = Frequencies()
        for item in data:
            freq.cadence.append(item.get("cadence", 0))
            freq.distance.append(item.get("distance", 0))
            freq.heart.append(item.get("heart", 0))
            freq.heartLevel.append(item.get("heartLevel", 0))
            freq.timestamp.append(item.get("timestamp", 0))
        return freq

    @staticmethod
    def get_summary_data(data) -> Summary:
        """Convert raw activity summary data to summary model."""
        return Summary(**data)

    @staticmethod
    def get_laps_data(data) -> list[Lap]:
        """Convert raw activity to laps data."""
        laps = []
        for item in data:
            if item["type"] == LapType.RUNNING:
                laps.extend(Lap(**lap) for lap in item["lapItemList"])
        return laps

    def extract_data(self) -> None:
        """Extract data from Coros API and build data models accordingly."""
        with requests.Session() as session:
            self._extract_data_inner(session)

    def _extract_data_inner(self, session: requests.Session) -> None:
        # get all activites
        activities = self.get_activities()
        self.activities = TrainActivities()
        for activity in activities:
            # extract raw data of an activity
            try:
                activity_data = self.get_raw_activity_data(session=session, activity=activity)
            except (requests.RequestException, RuntimeError):
                LOGGER.exception(
                    "Encountered error when processing activity, %r; continuing...",
                    activity,
                )
                continue

            # build pydantic models
            try:
                data_wrapped = activity_data["data"]
                activity = TrainActivity(
                    summary=CorosDataExtractor.get_summary_data(data_wrapped["summary"]),
                    data=CorosDataExtractor.get_activity_data(data_wrapped["frequencyList"]),
                    laps=CorosDataExtractor.get_laps_data(data_wrapped["lapList"]),
                )
            except KeyError:
                LOGGER.exception(
                    "Encountered error when processing activity, %r; continuing...",
                    data_wrapped,
                )
            else:
                self.activities.add_activity(activity)

    def to_json(self, filename: str = "activities.json") -> None:
        """Export data to json file."""
        if self.activities is not None:
            with Path(filename).open("w") as f:
                json.dump(self.activities.model_dump(), f, indent=2)
