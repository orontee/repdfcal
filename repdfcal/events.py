import datetime
from dataclasses import dataclass


@dataclass
class DailyEvent:
    start: datetime.datetime
    duration: int
    title: str

    def is_holiday(self) -> bool:
        return True
