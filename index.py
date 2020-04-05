import os
import asyncio
import logging
import threading

import flask
from flask import jsonify

from helpers.queryable_datetime import QueryableDateTime
from hotjar.api import HotjarAPI
from hotjar.site_manager import SiteManager

SECONDS = 60

_LOGGER = logging.getLogger(__name__)


class WebService:
    def __init__(self):
        self._username = None
        self._password = None
        self._interval = None
        self._specific_funnels = None

        self._is_updating = False
        self._api = None
        self._web_service = None
        self._site_managers = {}
        self._loop = asyncio.get_event_loop()

    async def initialize(self):
        self._username = os.getenv("HOTJAR_USERNAME")
        self._password = os.getenv("HOTJAR_PASSWORD")
        self._interval = int(os.getenv("HOTJAR_INTERVAL", 30)) * SECONDS

        specific_funnels = os.getenv("HOTJAR_FUNNELS", "")

        if len(specific_funnels) > 0:
            self._specific_funnels = specific_funnels.split(",")

        self._api = HotjarAPI(self._username, self._password)
        self._api.initialize()

        self._web_service = flask.Flask(__name__)
        self._web_service.config["DEBUG"] = True

        @self._web_service.route('/', methods=['GET'])
        def home():
            data = self.aggregate()

            return jsonify(data)

        @self._web_service.route('/flat', methods=['GET'])
        def flat():
            data = self.flatten()

            return jsonify(data)

        threading.Timer(0.1, self.update_data_once).start()

        self._web_service.run(host='0.0.0.0')

    def update_data_once(self):
        if self._is_updating:
            _LOGGER.warning(f"Skipping update data")

            return

        self._is_updating = True

        _LOGGER.debug("Updating data")

        resources = self._api.get_resources()

        sites = resources.get("sites", [])

        for site in sites:
            site_name = site.get("name")
            site_id = site.get("id")

            site_manager = self._site_managers.get(site_id)

            if site_manager is None:
                site_manager = SiteManager(self._api, site_id, site_name, self._specific_funnels)

                self._site_managers[site_id] = site_manager

            if site_id is not None:
                _LOGGER.debug(f"Site: {site_name} ({site_id})")

                site_manager.update()

        threading.Timer(self._interval, self.update_data_once).start()

        self._is_updating = False

    def aggregate(self):
        result = {}

        for site_id in self._site_managers:
            site_manager: SiteManager = self._site_managers[site_id]

            result[str(site_id)] = {
                "id": site_id,
                "name": site_manager.name,
                "funnels": site_manager.data
            }

        return result

    def flatten(self):
        data = self.aggregate()
        result = []

        for site_id in data:
            site_details = data[site_id]
            site_name = site_details.get("name")
            funnels = site_details.get("funnels", {})

            for funnel_id in funnels:
                funnel_details = funnels[funnel_id]
                funnel_name = funnel_details.get("name")
                funnel_created = funnel_details.get("created")
                funnel_steps = funnel_details.get("steps")

                for funnel_step_id in funnel_steps:
                    funnel_step = funnel_steps[funnel_step_id]
                    funnel_step_name = funnel_step.get("name")
                    funnel_step_url = funnel_step.get("url")
                    funnel_step_counters = funnel_step.get("counters")

                    for date in funnel_step_counters:
                        funnel_step_counter_data = funnel_step_counters[date]

                        count = int(funnel_step_counter_data.get("count"))
                        query_date = QueryableDateTime(funnel_step_counter_data.get("epoch"))

                        funnel_step_data = {
                            "site_id": site_id,
                            "site_name": site_name,
                            "funnel_id": funnel_id,
                            "funnel_name": funnel_name,
                            "funnel_created": funnel_created,
                            "funnel_step_id": funnel_step_id,
                            "funnel_step_name": funnel_step_name,
                            "funnel_step_url": funnel_step_url,
                            "date": query_date.date,
                            "date_iso": date,
                            "date_epoch": query_date.from_time,
                            "count": count
                        }

                        result.append(funnel_step_data)

        return result


web = WebService()
asyncio.get_event_loop().run_until_complete(web.initialize())


