import json
import math
import requests

from typing import Optional

from helpers.docker_logger import get_logger

from .const import *
from .exceptions import AuthorizationError

_LOGGER = get_logger(__name__)


class HotjarAPI:
    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password

        self._user_id = None
        self._access_key = None
        self._session = None

        self._logged_in = False

        self.headers = {
            "Content-Type": "application/json",
            "user-agent": HEADERS_USER_AGENT,
        }

    def initialize(self):
        try:
            self._session = requests.Session()
            self._session.headers = self.headers

            _LOGGER.debug("Initializing API connection")

            self._login(email=self._email, password=self._password)

            self._logged_in = True
        except Exception as ex:
            _LOGGER.error(f"Failed to initialize API connection for {self._email}, Error: {str(ex)}")

    def has_valid_session(self):
        can_perform = self._logged_in

        if not can_perform:
            self.initialize()

            can_perform = self._logged_in

        return can_perform

    def api_get_by_endpoint(self, site_id: int, endpoint: str, query_data: str = "", params: dict = {}):
        url = f"{QUERY_URL}/{site_id}/{endpoint}{query_data}"

        result = self.api_get(url, params)

        return result

    def api_get(self, url, params: dict = None):
        result = None

        for i in range(2):
            try:
                if self.has_valid_session():
                    session: requests.Session = self._session

                    response = session.get(url, params=params)

                    response.raise_for_status()

                    result = response.json()

                    if i > 0:
                        _LOGGER.info(f"API GET request performed on retry #{i + 1}, Url: {url}")

                    break
            except Exception as ex:
                self._logged_in = False

                if i + 1 == 2:
                    _LOGGER.error(f"Failed to perform API GET request #{i + 1}, Url: {url}, Error: {str(ex)}")
                else:
                    _LOGGER.warning(f"Failed to perform API GET request #{i + 1}, Url: {url}, Error: {str(ex)}")

        return result

    def get_current_user_info(self) -> dict:
        """
        Get current user info.

        :return: user info
        """
        response = self.api_get(USER_INFO_URL)
        return response

    def get_site_feed(self, site_id: int) -> list:
        """
        Get site feed.

        :param site_id: site id
        :return: site feed
        """
        response = self.api_get_by_endpoint(site_id, ENDPOINT_FEED)

        return response

    def get_site_funnels(self, site_id: int) -> dict:
        """
        Get site statistics.

        :param site_id: site id
        :return: site statistics
        """
        response = self.api_get_by_endpoint(site_id, ENDPOINT_FUNNELS)
        return response

    def get_site_funnel(self, site_id: int, funnel_id: int) -> dict:
        """
        Get site statistics.

        :param site_id: site id
        :return: site statistics
        """
        query_data = f"/{funnel_id}"
        response = self.api_get_by_endpoint(site_id, ENDPOINT_FUNNELS, query_data)
        return response

    def get_site_funnel_counters(self, site_id: int, funnel_id: int, from_date: float, to_date: float) -> dict:
        """
        Get site statistics.

        :param site_id: site id
        :return: site statistics
        """

        query_data = f"/{funnel_id}/counts?end_date={to_date}&start_date={from_date}"
        funnel_counters = self.api_get_by_endpoint(site_id, ENDPOINT_FUNNELS, query_data)

        return funnel_counters

    def get_site_statistics(self, site_id: int) -> dict:
        """
        Get site statistics.

        :param site_id: site id
        :return: site statistics
        """

        response = self.api_get_by_endpoint(site_id, ENDPOINT_STATISTICS)
        return response

    def get_resources(self, user_id: Optional[int] = None) -> dict:
        """
        Get sites and organizations info.
        If user_id is None, get currently logged user resources.

        :return: resources info
        """
        if not user_id:
            user_id = self._user_id

        url = f"https://insights.hotjar.com/api/v1/users/{user_id}/resources"
        response = self.api_get(url)

        return response

    def get_feedback_widgets(self, site_id: int) -> list:
        """
        Get all feedback widgets for specified site.

        :param site_id: site id
        :return: feedback widgets info
        """
        response = self.api_get_by_endpoint(site_id, ENDPOINT_FEEDBACK)
        return response

    def get_feedbacks(
        self,
        site_id: int,
        widget_id: int,
        _filter: str,
        limit: int = 100
    ) -> list:
        """
        Get feedback list.

        :param site_id: site id
        :param widget_id: feedback widget id
        :param _filter: filter
        get feedbacks received between 2019-01-01 and 2019-02-01:
        'created__ge__2019-01-01,created__le__2019-02-01'
        :param limit: feedbacks limit
        :return: feedback info, list
        """
        fields = [
            "browser",
            "content",
            "created_datetime_string",
            "created_epoch_time",
            "country_code",
            "country_name",
            "device",
            "id",
            "image_url",
            "index",
            "os",
            "response_url",
            "short_visitor_uuid",
            "thumbnail_url",
            "window_size",
        ]
        amount = 100
        result = []
        offset = 0
        count = self._get_feedbacks_count(
            _filter=_filter, site_id=site_id, widget_id=widget_id
        )

        limit = count if count < limit else limit

        for i in range(math.ceil(limit / 100)):
            params = dict(
                fields=",".join(fields),
                sort="-id",
                amount=amount,
                offset={offset},
                count=True,
                filter={_filter},
            )

            query_data = f"/{widget_id}/responses"
            response = self.api_get_by_endpoint(site_id, ENDPOINT_FEEDBACK, query_data, params)
            result += response["data"]

            offset += amount

        return result

    def get_sentiments(self, site_id: int, widget_id: int, _filter: str) -> dict:
        """
        Get user sentiments info.

        :param site_id: site id
        :param widget_id: feedback widget id
        :param _filter: filter
        :return: sentiments info
        """
        query_data = f"/{widget_id}/responses/sentiment"
        params = {"filter": _filter}

        response = self.api_get_by_endpoint(site_id, ENDPOINT_FEEDBACK, query_data, params)

        return response

    def _login(self, email: str, password: str) -> None:
        """
        Success response:
        {
            "access_key": "78e5aca7107e4ebaa77db80a0d8511a0",
            "success": true,
            "user_id": 9296871
        }

        :param email: user email
        :param password: user password
        :return: authorization info, dict
        """
        payload = {
            "action": "login",
            "email": email,
            "password": password,
            "remember": True,
        }

        session: requests.Session = self._session

        response = session.post(LOGIN_URL, data=json.dumps(payload))

        authorization_error = not response.status_code == 200

        if not authorization_error:
            result = response.json()

            self._user_id = result.get("user_id")
            self._access_key = result.get("access_key")

            authorization_error = self._access_key is None

        if authorization_error:
            raise AuthorizationError(response.text)

    def _get_feedbacks_count(self, site_id: int, widget_id: int, _filter: str) -> int:
        """
        Feedbacks count pre-request

        :param site_id: site id
        :param widget_id: feedback widget id
        :param limit: feedbacks limit
        :param _filter: filter
        :return: feedback info, list
        """
        query_data = f"/{widget_id}/responses"
        params = {
            "fields": "id",
            "amount": 0,
            "offset": 0,
            "count": "true",
            "filter": {_filter}
        }

        response = self.api_get_by_endpoint(site_id, ENDPOINT_FEEDBACK, query_data, params)

        return response["count"]
