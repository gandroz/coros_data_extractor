"""Common configuration variables."""

from urllib.parse import urljoin

BASE_URL = "https://teamapi.coros.com"

ACTIVITIES_URL = urljoin(BASE_URL, "/activity/query")
ACTIVITY_DETAILS_URL = urljoin(BASE_URL, "/activity/detail/query")
LOGIN_URL = urljoin(BASE_URL, "/account/login")


# NB: some values higher than 200, e.g., 438, seem to make the API barf.
ACTIVITY_PAGINATION_LIMIT = 200
DEFAULT_ACTIVITY_LIMIT = 200
