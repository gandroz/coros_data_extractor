"""Coros API translation logic.

This logic's intent is to provide a representation/meaning behind
"magic constants" provided by the Coros API.

Some of the constants were empirically derived through trial and error, while
other constants were found in the Coros API reference guide [1].

1. https://www.dropbox.com/scl/fo/6ps1297tn9pfo7qmcb0o8/AItfHWAW8t-jZ0NIrAaT0hg?preview=COROS+API+Reference+V2.0.6+(Updated+April+2025).pdf&rlkey=kbq4zmu47j9c3c6qu7b96z39f
"""

from enum import Enum


class ActivityFileType(Enum):
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


class ActivityType(Enum):
    """Activities can be of the following types.

    XXX: fill in more activity types.
    """

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
    """Bike rides and runs have specialized lap counters.

    These activities having specialized counters is extra confusing, in the
    grand scheme of things, since some other types of activities, e.g., hiking,
    can have laps associated with them as well (!).
    """

    BIKE_RIDE = 1
    RUNNING = 2
