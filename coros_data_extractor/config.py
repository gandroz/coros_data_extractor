"""Common configuration variables."""

from urllib.parse import urljoin

BASE_URL = "https://teamapi.coros.com"

ACTIVITIES_URL = urljoin(BASE_URL, "/activity/query")
ACTIVITY_DETAILS_URL = urljoin(BASE_URL, "/activity/detail/query")
LOGIN_URL = urljoin(BASE_URL, "/account/login")
