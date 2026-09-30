from typing import Optional

from dtos.response_status import ResponseStatus
from models.ticket import Ticket


class BookTicketResponseDTO:
    """The response: the booked ticket and whether it worked."""

    def __init__(self):
        self.status: Optional[ResponseStatus] = None
        self.ticket: Optional[Ticket] = None
