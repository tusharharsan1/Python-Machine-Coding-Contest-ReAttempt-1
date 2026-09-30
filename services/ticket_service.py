import threading
from datetime import datetime
from typing import List

from exceptions.invalid_show_seat_exception import InvalidShowSeatException
from exceptions.invalid_user_exception import InvalidUserException
from exceptions.seats_not_available_exception import SeatsNotAvailableException
from models.seat_status import SeatStatus
from models.ticket import Ticket
from models.ticket_status import TicketStatus
from repositories.show_seat_repository import ShowSeatRepository
from repositories.ticket_repository import TicketRepository
from repositories.user_repository import UserRepository


class TicketService:
    """Holds the business logic of booking a ticket.

    The repositories and a lock are already created for you in the constructor.
    ONE TicketService object is shared by all the users (threads) of the system.
    """

    def __init__(self, show_seat_repository: ShowSeatRepository,
                 ticket_repository: TicketRepository,
                 user_repository: UserRepository):
        self.show_seat_repository = show_seat_repository
        self.ticket_repository = ticket_repository
        self.user_repository = user_repository
        # Only ONE thread at a time can be inside `with self._lock:`. Any other thread waits for its turn.
        self._lock = threading.Lock()

    def book_ticket(self, show_seat_ids: List[int], user_id: int) -> Ticket:
        """Books a ticket for the user: blocks the requested show seats and returns an UNPAID ticket.

        Raises:
            InvalidUserException: if the user does not exist.
            InvalidShowSeatException: if some show seat id does not exist (or the list is empty / has repeats).
            SeatsNotAvailableException: if any of the seats is BLOCKED or BOOKED. Nothing is booked then.
        """

        # TODO Step 1: Put ALL the steps below inside the lock:
        #       with self._lock:
        #           ...steps 2 to 7, indented...
        #   Why? Two users can both read "this seat is AVAILABLE" before either of them blocks it,
        #   and then both would get the seat. Only one thread at a time can be in the `with` block, so the
        #   second user reads the seat only AFTER the first user has already blocked it.

        # TODO Step 2: Validate the user.
        #   Get the user with self.user_repository.find_by_id(user_id).
        #   If there is no such user, raise InvalidUserException("...some message...").

        # TODO Step 3: Fetch the requested show seats.
        #   show_seats = self.show_seat_repository.find_show_seats_by_id_in(show_seat_ids)
        #   Every requested id must have been found, so the number of show seats you got must be equal to
        #   len(show_seat_ids). If not (unknown id, repeated id) or if the list is empty,
        #   raise InvalidShowSeatException("...some message...").
        #   Then get the show:  show = show_seats[0].show   (all the seats belong to the same show)

        # TODO Step 4: Check that ALL the show seats are AVAILABLE.
        #   Collect the ids of the show seats whose status is NOT SeatStatus.AVAILABLE into a list.
        #   If this list is not empty, raise SeatsNotAvailableException with a message like
        #   "Seats are not available: [3, 4]" (the ids of the unavailable show seats).
        #   Do this check for ALL the seats BEFORE you change any seat.

        # TODO Step 5: Mark every show seat as blocked: show_seat.status = SeatStatus.BLOCKED
        #   You do not need to save them separately. SQLAlchemy notices the change, and it is saved
        #   together with the ticket in the next step.

        # TODO Step 6: Create a Ticket and save it.
        #   ticket = Ticket()
        #   ticket.seats = the Seat of every show seat (show_seat.seat)
        #   ticket.show = the show from Step 3
        #   ticket.time_of_booking = datetime.now()
        #   ticket.user = the user from Step 2
        #   ticket.status = TicketStatus.UNPAID
        #   ticket = self.ticket_repository.save(ticket)

        # TODO Step 7: Return the saved ticket (and delete the line `return None` below).

        return None
