from enum import Enum, auto


class ScreenStatus(Enum):
    OPERATIONAL = auto()
    UNDER_MAINTENANCE = auto()
    CLOSED = auto()
