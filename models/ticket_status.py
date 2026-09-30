from enum import Enum, auto


class TicketStatus(Enum):
    BOOKED = auto()
    CANCELLED = auto()
    UNPAID = auto()
