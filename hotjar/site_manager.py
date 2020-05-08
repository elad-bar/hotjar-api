import json

from os import path

from datetime import datetime

from helpers.docker_logger import get_logger
from helpers.queryable_datetime import QueryableDateTime

from .api import HotjarAPI
from .const import *

_LOGGER = get_logger(__name__)


class SiteManager:
    def __init__(self, api: HotjarAPI, site_id: int, site_name: str, created, specific_funnels: list, environment):
        self._api = api
        self._site_id = site_id
        self._site_name = site_name
        self._created = created
        self._specific_funnels = specific_funnels
        self._file = f"/data/site_{self._site_id}_v{VERSION}.json"
        self._updates = []

        if environment != DEFAULT_ENVIRONMENT:
            self._file = self._file.replace("/data/", "")

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
                try:
                    self._data = json.load(json_file)

                except Exception as ex:
                    _LOGGER.error(f"Failed to load previous state, starting from day 1, Error: {ex}")
                    self._data = {}

        else:
            self._data = {}

    def _save_data(self):
        with open(self._file, "w") as outfile:
            json.dump(self.data, outfile)

    def update(self):
        _LOGGER.info(f"Updating site: {self._site_name} ({self._site_id})")

        all_funnels = self._api.get_site_funnels(self._site_id)

        if all_funnels is None:
            _LOGGER.error("Could not load funnels from API")
        else:
            for funnel in all_funnels:
                funnel_name = funnel.get(PROP_NAME)
                funnel_id = funnel.get(PROP_ID)
                funnel_key = str(funnel_id)

                if self._specific_funnels is not None and funnel_key not in self._specific_funnels:
                    _LOGGER.debug(f"Skipping funnel: {funnel_name} ({funnel_id})")
                    continue

                _LOGGER.debug(f"Processing funnel: {funnel_name} ({funnel_id})")

                funnel_details = self._api.get_site_funnel(self._site_id, funnel_id)

                if funnel_details is None:
                    _LOGGER.error(f"Could not load funnel {funnel_name} ({funnel_id}) from API")
                else:
                    self.load_funnel(funnel_id, funnel_details)

            for funnel_key in self._data:
                funnel = self._data[funnel_key]
                funnel_id = funnel.get(PROP_ID)

                self.load_funnel_counters(funnel_id)

            changes_count = len(self._updates)

            self._updates = []

            if changes_count > 0:
                _LOGGER.info(f"Site {self._site_name} ({self._site_id}) is updated")

                self._save_data()
            else:
                _LOGGER.info(f"Site {self._site_name} ({self._site_id}) was up to date")

    @staticmethod
    def get_date_iso(epoch):
        return datetime.fromtimestamp(epoch).date().isoformat()

    def get_funnel_data(self, funnel_id):
        funnel_data = self._data[str(funnel_id)]

        return funnel_data

    def load_funnel(self, funnel_id, funnel_details):
        funnel_key = str(funnel_id)
        updated = False

        if funnel_details is not None:
            funnel_name = funnel_details.get(PROP_NAME)

            created_date = funnel_details.get(PROP_CREATED_EPOCH_TIME)
            created_date_iso = self.get_date_iso(created_date)

            latest_steps = funnel_details.get(PROP_STEPS)
            steps = {}

            if funnel_key not in self._data:
                funnel_data = {
                    PROP_NAME: funnel_name,
                    PROP_ID: funnel_id,
                    PROP_CREATED: created_date,
                    PROP_CREATED_ISO: created_date_iso,
                    PROP_STEPS: steps,
                }

                _LOGGER.info(f"Funnel data created: {funnel_data}")

                self._data[funnel_key] = funnel_data
                updated = True

            steps_updated = self.load_funnel_steps(steps, latest_steps)

            updated = updated or steps_updated

        if updated and funnel_id not in self._updates:
            self._updates.append(funnel_id)

    def load_funnel_counters(self, funnel_id):
        changed = False

        funnel_data = self.get_funnel_data(funnel_id)
        if funnel_data is not None:
            funnel_name = funnel_data.get(PROP_NAME)
            last_update = funnel_data.get(PROP_LAST_UPDATE, self._created)

            steps = funnel_data[PROP_STEPS]

            last_update_query = QueryableDateTime(last_update)
            all_dates = last_update_query.get_all_since()

            for item in all_dates:
                date_query: QueryableDateTime = item
                date_iso = date_query.date.date().isoformat()

                funnel_data[PROP_LAST_UPDATE] = date_query.from_time
                funnel_data[PROP_LAST_UPDATE_ISO] = date_iso

                _LOGGER.info(f"Processing funnel: {funnel_name} ({funnel_id}), counter from: {date_iso}")

                funnel_counters = self._api.get_site_funnel_counters(self._site_id,
                                                                     funnel_id,
                                                                     date_query.from_time,
                                                                     date_query.to_time)

                if funnel_counters is None:
                    _LOGGER.error(f"Could not load funnel {funnel_name} ({funnel_id}) counters for {date_iso} from API")
                else:
                    visit_counts_per_step = funnel_counters.get(PROP_VISIT_COUNTS_PER_STEP, {})

                    for key in visit_counts_per_step:
                        step: dict = steps[key]
                        counters = step[PROP_COUNTERS]

                        count = visit_counts_per_step[key]

                        if date_iso not in counters or counters[date_iso][PROP_COUNT] != count:
                            counters[date_iso] = {
                                PROP_EPOCH: date_query.from_time,
                                PROP_COUNT: count
                            }

                            changed = True

        if changed and funnel_id not in self._updates:
            self._updates.append(funnel_id)

    @staticmethod
    def load_funnel_steps(steps, external_funnel_steps):
        changed = False

        for funnel_step in external_funnel_steps:
            step_id = funnel_step.get(PROP_ID)
            step_name = funnel_step.get(PROP_NAME)
            step_url = funnel_step.get(PROP_URL)

            _LOGGER.debug(f"Processing funnel's step: {step_name} ({step_id})")

            step_key = str(step_id)

            step = steps.get(step_key)

            if step is None:
                step = {
                    PROP_ID: step_id,
                    PROP_NAME: step_name,
                    PROP_URL: step_url,
                    PROP_COUNTERS: {}
                }

                if step_key not in steps or steps[step_key] != step:
                    steps[step_key] = step

                    _LOGGER.info(f"Funnel's step changed: {step}")

                    changed = True

        return changed
