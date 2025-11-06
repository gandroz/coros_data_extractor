"""Coros data extractor from Training Hub.

This module contains the core logic associated with downloading data from the Coros API
and messaging it into data structures representing what the API provided.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import pathlib
import time
import typing

import requests

from coros_data_extractor.model import (
    Frequencies,
    Lap,
    Summary,
    TrainActivities,
    TrainActivity,
)

from .api_model import (
    ActivityFileType,
    ActivityType,
    LapType,
)
from .constants import (
    ACTIVITIES_URL,
    ACTIVITY_DETAILS_URL,
    ACTIVITY_DOWNLOAD_URL,
    ACTIVITY_PAGINATION_LIMIT,
    DEFAULT_ACTIVITY_QUERY_LIMIT,
    GET_ACTIVITY_QUERY_TIMEOUT,
    LOGIN_URL,
    RAW_ACTIVITY_QUERY_API_TIMEOUT,
    SIMPLE_QUERY_API_TIMEOUT,
)

# ruff: noqa: S324


logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s: %(levelname)s: %(asctime)s %(message)s",
)
LOGGER = logging.getLogger(__name__)
MAX_TRIES = 3
WAIT_BETWEEN_RETRIES = 0.5


class CorosDataExtractor:
    """Coros data extractor from Training Hub."""

    def __init__(
        self,
        default_activity_query_limit: int | None = DEFAULT_ACTIVITY_QUERY_LIMIT,
    ) -> None:
        """Initialize extractor."""
        self.access_token = None
        self.activities = None
        self.user_id = None
        self.default_activity_query_limit = default_activity_query_limit

    def login(self, account: str, password: str) -> None:
        """Login to Coros API.

        Args:
            account: a humanized identifier associated with an account.
                     This can be an email address or phone number.
            password: the password for `account`.

        """
        request_data = {
            "account": account,
            "accountType": 2,
            "pwd": hashlib.md5(password.encode()).hexdigest(),
        }
        resp = requests.post(
            LOGIN_URL,
            json=request_data,
            timeout=SIMPLE_QUERY_API_TIMEOUT,
        )
        resp.raise_for_status()
        data_wrapped = resp.json()["data"]
        self.access_token = data_wrapped["accessToken"]
        self.user_id = data_wrapped["userId"]

    def export_activities(
        self,
        file_type: ActivityFileType,
        output_directory: pathlib.Path,
        activity_types: ... = None,
        limit: int | None = None,
    ) -> None:
        """Export activities of a specific file type from the Coros API.

        Args:
            file_type:          a file type to export data for, e.g.,
                                `ActivityFileType.GPX`.
            output_directory:   the directory to export the data to. This path must
                                already exist.
            activity_types:     Activity types to export data for.
            limit:              The maximum number of activities to export.

        """
        with requests.Session() as dl_session, requests.Session() as query_session:
            self._export_activities_inner(
                dl_session,
                query_session,
                file_type,
                output_directory,
                activity_types=activity_types,
                limit=limit,
            )

    def _export_activities_inner(
        self,
        download_session: requests.Session,
        query_session: requests.Session,
        file_type: ...,
        output_directory: ...,
        activity_types: ... = None,
        limit: ... = None,
    ) -> None:
        """Export activities of a specific file type from the Coros API (inner).

        Args:
            download_session: the HTTP session which will be used to download the
                              exported activities.
            query_session:    the HTTP session which will be used to query for
                              exported activities.
            file_type:        see description under `.export_activities(..)`.
            output_directory: see description under `.export_activities(..)`.
            activity_types:   see description under `.export_activities(..)`.
            limit:            see description under `.export_activities(..)`.

        """
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

        activities = self.get_activities(
            activity_types=activity_types,
            limit=limit,
        )
        headers = {"Accesstoken": self.access_token}

        for activity in activities:
            activity_name = activity["name"]
            activity_start_time = activity["startTime"]
            label_id = activity["labelId"]
            sport_type_raw = activity["sportType"]
            try:
                sport_type = ActivityType(sport_type_raw)
            except Exception:
                LOGGER.debug(
                    "Sport type=%d not supported by ActivityType. Metadata: "
                    "startTimestamp=%r, name=%r, label_id=%r",
                    sport_type_raw,
                    activity_start_time,
                    activity_name,
                    label_id,
                    exc_info=True,
                )
            else:
                if not sport_type.supports_export(file_type):
                    LOGGER.debug(
                        "Skipping file export for ActivityType with label_id=%r; "
                        "does not support file type=%s",
                        label_id,
                        file_type.name,
                    )
                    continue

            # https://teamapi.coros.com/activity/query?size=10&pageNumber=1&modeList=
            payload = {
                "labelId": label_id,
                "fileType": file_type.value,
                "sportType": sport_type_raw,
            }

            resp = query_session.post(
                ACTIVITY_DOWNLOAD_URL,
                headers=headers,
                data=payload,
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
                    file_type.name,
                    sport_type,
                    resp_json,
                )
                continue

            download_url = resp_json["data"]["fileUrl"]
            resp = download_session.get(download_url, stream=True)
            filename = f"{activity_start_time}_{activity_name}_{label_id}.{extension}"

            LOGGER.debug(
                "Downloading file with %s from %s to %s",
                label_id,
                download_url,
                filename,
            )
            (output_directory / filename).write_bytes(resp.raw.read())

    def get_activities(
        self,
        activity_types: list[ActivityType] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Extract list of activities from API.

        Args:
            limit: a maximum number of activities to get in a single query.
            activity_types: a list of types to get activities for, or `None` to
                            fetch all activities.

        """
        with requests.Session() as session:
            return self._get_activities_inner(
                session,
                activity_types=activity_types,
                limit=limit,
            )

    def _get_activities_inner(
        self,
        session: requests.Session,
        activity_types: ...,
        limit: ...,
    ) -> dict:
        """Extract list of activities from API (inner).

        Args:
            session:        HTTP session used to query for activities.
            activity_types: a list of types to get activities for, or `None` to
                            fetch all activities.
            limit:          a maximum number of activities to get in a single query.

        Returns:
            Activity data as presented by Coros, i.e., the "data" -> "dataList" key in
            the raw JSON.

        """
        if activity_types is None:
            mode_list = ""
        else:
            mode_list = ",".join(str(activity_type) for activity_type in activity_types)

        if limit is None:
            limit = self.default_activity_query_limit

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
                ACTIVITIES_URL,
                headers=headers,
                params=payload,
                timeout=GET_ACTIVITY_QUERY_TIMEOUT,
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
                timeout=SIMPLE_QUERY_API_TIMEOUT,
            )
            resp.raise_for_status()
            res = resp.json()

            datalist.extend(res["data"]["dataList"])

        return datalist

    @staticmethod
    def valid_raw_activity_data(resp_json: dict) -> bool:
        """Answer whether or not `resp_json` is a valid JSON activity payload.

        Args:
            resp_json: a JSON blob to interrogate for validity.

        Returns:
            True if valid; False otherwise.

        """
        return resp_json.get("data", {}).get("summary") is not None

    def get_raw_activity_data(
        self,
        session: requests.Session,
        activity: dict,
        max_tries: int = MAX_TRIES,
        wait_between_retries: float = WAIT_BETWEEN_RETRIES,
    ) -> dict:
        """Extract raw activity data from `activity`.

        Args:
            session: the HTTP session to query activity data from.
            activity: the JSON blob that denotes an activity to query data for.
            max_tries: the maximum number of tries to use when downloading the
                       raw activity data.
            wait_between_retries: time to sleep between attempts.

        Returns:
            Raw activity data in `dict` form.

        Raises:
            RuntimeError: the activity data could not be downloaded.

        """
        for retries_left in range(max_tries - 1, -1, -1):
            try:
                resp_json = self._get_raw_activity_data_inner(
                    session,
                    activity,
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
                time.sleep(wait_between_retries)

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
        """Extract raw activity data from `activity` (inner).

        This method processes a single request.

        Args:
            session: the HTTP session to query activity data from.
            activity: the JSON blob that denotes an activity to query data for.

        Returns:
            A JSON blob representing a potential activity.

        Raises:
            requests.exceptions.HTTPError: a problem occurred when making/handling
                                           the request.

        """
        payload = {
            "labelId": activity["labelId"],
            "sportType": activity["sportType"],
            "screenW": 944,
            "screenH": 1440,
        }
        headers = {"Accesstoken": self.access_token}
        resp = session.post(
            ACTIVITY_DETAILS_URL,
            headers=headers,
            params=payload,
            timeout=RAW_ACTIVITY_QUERY_API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def get_activity_data(data: dict) -> Frequencies:
        """Convert raw activity data to a time series representation."""
        freq = Frequencies()
        for item in data:
            freq.cadence.append(item.get("cadence", 0))
            freq.distance.append(item.get("distance", 0))
            freq.heart.append(item.get("heart", 0))
            freq.heartLevel.append(item.get("heartLevel", 0))
            freq.timestamp.append(item.get("timestamp", 0))
        return freq

    @staticmethod
    def get_summary_data(data: dict) -> Summary:
        """Convert raw activity summary data to summary model.

        Args:
            data: a JSON blob which represents a potential activity JSON payload.

        Returns:
            A summary of the activity.

        """
        return Summary(**data)

    @staticmethod
    def get_laps_data(
        sport_type: ActivityType,
        raw_lap_data: dict[str, typing.Any],
    ) -> list[Lap]:
        """Convert raw activity to laps data.

        Args:
            sport_type:     The sport type for the activity data.
            raw_lap_data:   The raw lap activity data.

        Returns:
            A list of Lap objects for the provided activity.

        """
        if sport_type not in ActivityType.RUN_ACTIVITY_TYPES:
            return []

        laps = []
        for item in raw_lap_data:
            if item["type"] == LapType.RUNNING:
                laps.extend(Lap(**lap) for lap in item["lapItemList"])
            # XXX: item["type"] == LapType.BIKING:
        return laps

    def extract_data(
        self,
        activity_types: ... = None,
        limit: ... = None,
    ) -> None:
        """Extract data from Coros API & build data models accordingly."""
        with requests.Session() as session:
            self._extract_data_inner(
                session,
                activity_types=activity_types,
                limit=limit,
            )

    def _extract_data_inner(
        self,
        session: requests.Session,
        activity_types: ... = None,
        limit: ... = None,
    ) -> None:
        """Extract data from Coros API & build data models accordingly (inner)."""
        # Get activites
        activities = self.get_activities(
            activity_types=activity_types,
            limit=limit,
        )
        self.activities = TrainActivities()
        for activity in activities:
            sport_type = activity["sportType"]

            # Extract raw data of an activity.
            try:
                activity_data = self.get_raw_activity_data(
                    session=session,
                    activity=activity,
                )
            except (requests.RequestException, RuntimeError):
                LOGGER.exception(
                    "Encountered error when processing activity, %r; continuing...",
                    activity,
                )
                continue

            # Build pydantic models for the activity.
            try:
                data_wrapped = activity_data["data"]
                training_activity = TrainActivity(
                    summary=self.get_summary_data(data_wrapped["summary"]),
                    data=self.get_activity_data(data_wrapped["frequencyList"]),
                    laps=self.get_laps_data(sport_type, data_wrapped["lapList"]),
                )
            except KeyError:
                LOGGER.exception(
                    "Encountered error when processing activity, %r; continuing...",
                    activity,
                )
            else:
                self.activities.add_activity(training_activity)

    def to_json(
        self,
        filename: str,
    ) -> None:
        """Export data to a JSON file.

        Args:
            filename:           the export filename (basename only).

        """
        if self.activities is None:
            LOGGER.debug(
                "No activities have been imported [yet]. "
                "Hint: call `.extract_data(..)` first.",
            )
            return

        with pathlib.Path(filename).open("w") as file_obj:
            json.dump(self.activities.model_dump(), file_obj, indent=2)
