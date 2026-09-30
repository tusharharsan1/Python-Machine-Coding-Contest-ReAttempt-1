from enum import Enum, auto


class SeatStatus(Enum):
    AVAILABLE = auto()
    BOOKED = auto()
    BLOCKED = auto()
