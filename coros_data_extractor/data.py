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
    ACTIVITY_DOWNLOAD_URL,
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


class ActivityFileType(Enum):
    CSV = 0
    GPX = 1
    KML = 2
    TCX = 3
    FIT = 4


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
        self.access_token = None
        self.activities = None
        self.user_id = None

    def login(self, account: str, password: str) -> None:
        """Login to Coros API."""
        request_data = {
            "account": account,
            "accountType": 2,
            "pwd": hashlib.md5(password.encode()).hexdigest(),
        }
        resp = requests.post(LOGIN_URL, json=request_data, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data_wrapped = resp.json()["data"]
        self.access_token = data_wrapped["accessToken"]
        self.user_id = data_wrapped["userId"]

    def export_activities(
        self,
        file_type: ActivityFileType,
    ) -> None:
        with requests.Session() as download_session, requests.Session() as query_session:
            self._export_activities_inner(download_session, query_session, file_type)

    def _export_activities_inner(
        self,
        download_session: requests.Session,
        query_session: requests.Session,
        file_type: ...,
    ) -> None:

        match file_type:
            case ActivityFileType.CSV:
                extension = "csv"
            case ActivityFileType.FIT:
                extension = "fit"
            case ActivityFileType.GPX:
                extension = "gpx"
            case ActivityFileType.KML:
                extension = "kml"
            case ActivityFileType.TCX:
                extension = "tcx"

        activities = self.get_activities()
        headers = {"Accesstoken": self.access_token}

        for activity in activities:
            # extract raw data of an activity
            label_id = activity["labelId"]
            try:
                activity_data = self.get_raw_activity_data(
                    session=query_session, activity=activity,
                )
            except (requests.RequestException, RuntimeError):
                LOGGER.exception(
                    "Encountered error when processing activity, %r; continuing...",
                    activity,
                )
                continue
            else:
                activity_summary = self.get_summary_data(
                    activity_data["data"]["summary"]
                )

            sport_type = activity["sportType"]
            payload = {
                "labelId": label_id,
                "fileType": file_type.value,
                "sportType": sport_type,
            }

            resp = query_session.post(
                ACTIVITY_DOWNLOAD_URL, headers=headers, data=payload,
            )
            resp.raise_for_status()
            resp_json = resp.json()
            if "data" not in resp_json:
                # NB: not all file formats are guaranteed to be available to download.
                #
                # I wish Coros returned something sensible, but they probably did this
                # to avoid the pain of dealing with direct error handling in their
                # JS/TS.
                #
                # XXX: dig through the dev docs to try and glean which ones are
                # supported with which types.
                LOGGER.info(
                    "Could not download %s file type; is it supported with sport "
                    "type=%s? Response from server: %s",
                    file_type.name, sport_type, resp_json,
                )
                continue

            download_url = resp_json["data"]["fileUrl"]
            resp = download_session.get(download_url, stream=True)
            filename = "_".join([
                activity_summary.startTimestamp.isoformat(),
                activity_summary.name,
                label_id,
            ]) + f".{extension}"

            LOGGER.debug(
                "Downloading file with %d from %s to %s",
                label_id, download_url, filename,
            )

            with (Path("exports") / filename).open("wb") as fp:
                fp.write(resp.raw.read())

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
