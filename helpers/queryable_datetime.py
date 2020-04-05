import datetime


class QueryableDateTime(object):
    def __init__(self, epoch: float):
        self._epoch = epoch
        self._date = self._get_date_from_epoch(epoch)

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def from_time(self) -> int:
        return int(self.date.timestamp())

    @property
    def to_time(self) -> int:
        to_time = datetime.datetime(self.date.year, self.date.month, self.date.day, 23, 59, 59)

        return int(to_time.timestamp())

    @staticmethod
    def _get_date_from_epoch(epoch) -> datetime:
        date = datetime.datetime.fromtimestamp(epoch)

        return date

    def __repr__(self):
        return f"Date: {self.date}, From: {self.from_time}, To: {self.to_time}"

    def _get_epoch_since(self) -> list:
        start_date = self._date
        today = datetime.datetime.today()
        days_since = (today - start_date).days

        dates = []

        for i in range(days_since + 1):
            day = start_date + datetime.timedelta(days=i)
            current_date = datetime.datetime(day.year, day.month, day.day)

            dates.append(current_date.timestamp())

        return dates

    def get_all_since(self) -> list:
        epoch_list = self._get_epoch_since()
        result = []

        for epoch in epoch_list:
            queryable_datetime = QueryableDateTime(epoch)

            result.append(queryable_datetime)

        return result