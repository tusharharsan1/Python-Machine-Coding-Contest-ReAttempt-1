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

        # Step 1: only one thread at a time can run the steps below.
        # Without the lock, two users could both read "this seat is AVAILABLE" before either of them
        # blocks it, and both would get the seat.
        with self._lock:

            # Step 2: the user must exist
            user = self.user_repository.find_by_id(user_id)
            if user is None:
                raise InvalidUserException(f"User with id {user_id} not found")

            # Step 3: every requested show seat must exist
            show_seats = self.show_seat_repository.find_show_seats_by_id_in(show_seat_ids)
            if len(show_seat_ids) == 0 or len(show_seats) != len(show_seat_ids):
                raise InvalidShowSeatException("Some of the show seat ids are invalid")
            show = show_seats[0].show  # all the seats belong to the same show

            # Step 4: every show seat must be AVAILABLE. We check ALL of them before changing anything.
            unavailable_ids = []
            for show_seat in show_seats:
                if show_seat.status != SeatStatus.AVAILABLE:
                    unavailable_ids.append(show_seat.id)
            if len(unavailable_ids) > 0:
                raise SeatsNotAvailableException(f"Seats are not available: {sorted(unavailable_ids)}")

            # Step 5: block all the show seats (saved together with the ticket in the next step)
            for show_seat in show_seats:
                show_seat.status = SeatStatus.BLOCKED

            # Step 6: create the ticket and save it
            ticket = Ticket()
            ticket.seats = [show_seat.seat for show_seat in show_seats]
            ticket.show = show
            ticket.time_of_booking = datetime.now()
            ticket.user = user
            ticket.status = TicketStatus.UNPAID
            ticket = self.ticket_repository.save(ticket)

            # Step 7: return the saved ticket
            return ticket
