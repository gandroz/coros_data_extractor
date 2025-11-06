"""Coros API translation logic.

This logic's intent is to provide a representation/meaning behind
"magic constants" provided by the Coros API.

Some of the constants were empirically derived through trial and error, while
other constants were found in the Coros API reference guide [1].

1. https://www.dropbox.com/scl/fo/6ps1297tn9pfo7qmcb0o8/AItfHWAW8t-jZ0NIrAaT0hg?preview=COROS+API+Reference+V2.0.6+(Updated+April+2025).pdf&rlkey=kbq4zmu47j9c3c6qu7b96z39f
"""

import enum


@enum.unique
class ActivityFileType(enum.IntEnum):
    """Activity data export file types.

    - CSV: comma separated values.
    - GPX: GPS XML data format.
    - KML: Google Earth datapoints.
    - TCX: Garmin Training Center XML.
    - FIT: flexible and interoperable data transfer format. This file format was
           created by Garmin.
    """

    CSV = 0
    GPX = 1
    KML = 2
    TCX = 3
    FIT = 4

    POSITIONAL_DATA_FILE_TYPE = enum.nonmember(
        (
            GPX,
            KML,
        )
    )


@enum.unique
class ActivityType(enum.IntEnum):
    """Activities can be of the following types.

    XXX: fill in more activity types.

    Known missing types:
    - TRAIL_RUN
    - CROSSCOUNTRY_SKI
    - TRACK_RUN
    - GRAVEL_BIKE
    - OUTDOOR_CLIMB
    - MOUNTAIN_CLIMB
    """

    OUTDOOR_RUN = 100
    INDOOR_RUN = 101
    HIKE = 104
    ROAD_BIKE = 200
    INDOOR_BIKE = 201
    MOUNTAIN_BIKE = 204
    GYM_CARDIO = 400
    SKI = 500
    SNOWBOARD = 501
    SKI_TOURING = 503
    INDOOR_CLIMB = 800
    BOULDERING = 801
    OUTDOOR_CLIMB = 802
    WALK = 900
    JUMP_ROPE = 901
    ELLIPTICAL = 903
    YOGA = 904
    MULTISPORT = 10001

    def supports_export(
        self,
        file_type: ActivityFileType,
    ) -> bool:
        if file_type in ActivityFileType.POSITIONAL_DATA_FILE_TYPE:
            return self.value in self.ACTIVITY_TYPE_SUPPORTS_POSITIONAL_DATA
        return True

    OUTDOOR_BIKE_ACTIVITY_TYPES = enum.nonmember(
        {
            ROAD_BIKE,
            MOUNTAIN_BIKE,
        }
    )
    OUTDOOR_CLIMB_ACTIVITY_TYPES = enum.nonmember(
        {
            OUTDOOR_CLIMB,
            BOULDERING,
        }
    )
    OUTDOOR_SNOWSPORT_ACTIVITY_TYPES = enum.nonmember(
        {
            SKI,
            SKI_TOURING,
            SNOWBOARD,
        }
    )

    BIKE_ACTIVITY_TYPES = enum.nonmember({INDOOR_BIKE} | OUTDOOR_BIKE_ACTIVITY_TYPES)

    RUN_ACTIVITY_TYPES = enum.nonmember(
        (
            INDOOR_RUN,
            OUTDOOR_RUN,
        )
    )

    ACTIVITY_TYPE_SUPPORTS_POSITIONAL_DATA = enum.nonmember(
        {
            OUTDOOR_RUN,
            HIKE,
            WALK,
            MULTISPORT,
        }
        | OUTDOOR_CLIMB_ACTIVITY_TYPES
        | OUTDOOR_SNOWSPORT_ACTIVITY_TYPES
        | OUTDOOR_BIKE_ACTIVITY_TYPES
    )


@enum.unique
class LapType(enum.IntEnum):
    """Bike rides and runs have specialized lap counters.

    These activities having specialized counters is extra confusing, in the
    grand scheme of things, since some other types of activities, e.g., hiking,
    can have laps associated with them as well (!).

    XXX: what about these types? They have laps associated with them--on the
         site/Strava at least.
    - SKI
    - SKI_TOURING
    - SNOWBOARDING
    """

    BIKE_RIDE = 1
    RUNNING = 2
