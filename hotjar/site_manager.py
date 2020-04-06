import json

from os import path

from datetime import datetime

from helpers.docker_logger import get_logger
from helpers.queryable_datetime import QueryableDateTime
from .api import HotjarAPI

_LOGGER = get_logger(__name__)


class SiteManager:
    def __init__(self, api: HotjarAPI, site_id: int, site_name: str, specific_funnels: list):
        self._api = api
        self._site_id = site_id
        self._site_name = site_name
        self._specific_funnels = specific_funnels
        self._file = f"/data/site_{self._site_id}.json"

        self._data = None

        self._load_data()

    @property
    def name(self):
        return self._site_name

    @property
    def data(self):
        return self._data

    def _load_data(self):
        if path.exists(self._file):
            with open(self._file) as json_file:
                self._data = json.load(json_file)
        else:
            self._data = {}

    def _save_data(self):
        with open(self._file, "w") as outfile:
            json.dump(self.data, outfile)

    def update(self):
        _LOGGER.debug(f"Updating site: {self._site_name} ({self._site_id})")

        all_funnels = self._api.get_site_funnels(self._site_id)

        for funnel in all_funnels:
            funnel_name = funnel.get("name")
            funnel_id = funnel.get("id")

            if self._specific_funnels is not None and str(funnel_id) not in self._specific_funnels:
                _LOGGER.debug(f"Skipping funnel: {funnel_name} ({funnel_id})")
                continue

            _LOGGER.debug(f"Processing funnel: {funnel_name} ({funnel_id})")

            funnel_details = self._api.get_site_funnel(self._site_id, funnel_id)
            created_epoch_time = funnel_details.get("created_epoch_time")

            funnel_data = self._data.get(str(funnel_id))

            if funnel_data is None:
                funnel_data = {
                    "name": funnel_name,
                    "id": funnel_id,
                    "created": created_epoch_time,
                    "created_iso": datetime.fromtimestamp(created_epoch_time).date().isoformat(),
                    "last_update": created_epoch_time,
                    "last_update_iso": datetime.fromtimestamp(created_epoch_time).date().isoformat(),
                    "steps": {}
                }

                self._data[funnel_id] = funnel_data

            last_update = funnel_data.get("last_update", created_epoch_time)
            last_update_query = QueryableDateTime(last_update)
            all_dates = last_update_query.get_all_since()

            steps = funnel_data["steps"]

            external_funnel_steps = funnel_details["steps"]

            for funnel_step in external_funnel_steps:
                step_id = funnel_step.get("id")
                step_name = funnel_step.get("name")
                step_url = funnel_step.get("url")

                _LOGGER.debug(f"Processing funnel: {funnel_name} ({funnel_id}), step: {step_name} ({step_id})")

                step = steps.get(str(step_id))

                if step is None:
                    step = {
                        "id": step_id,
                        "name": step_name,
                        "url": step_url,
                        "counters": {}
                    }

                    steps[str(step_id)] = step

            for item in all_dates:
                date_query: QueryableDateTime = item
                date_iso = date_query.date.date().isoformat()

                funnel_data["last_update"] = date_query.from_time
                funnel_data["last_update_iso"] = date_iso

                _LOGGER.debug(f"Processing funnel: {funnel_name} ({funnel_id}), counter from: {date_iso}")

                funnel_counters = self._api.get_site_funnel_counters(self._site_id,
                                                                     funnel_id,
                                                                     date_query.from_time,
                                                                     date_query.to_time)

                visit_counts_per_step = funnel_counters.get("visit_counts_per_step", {})

                for key in visit_counts_per_step:
                    step: dict = steps[key]
                    counters = step["counters"]

                    count = visit_counts_per_step[key]

                    counters[date_iso] = {
                        "epoch": date_query.from_time,
                        "count": count
                    }

        self._save_data()
