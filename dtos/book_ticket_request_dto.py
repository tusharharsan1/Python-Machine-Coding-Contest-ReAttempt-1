from typing import List


class BookTicketRequestDTO:
    """The request: who wants to book, and which show seats."""

    def __init__(self, show_seat_ids: List[int], user_id: int):
        self.show_seat_ids = show_seat_ids
        self.user_id = user_id
