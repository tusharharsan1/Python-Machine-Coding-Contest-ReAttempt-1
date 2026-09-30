"""A small demo that shows how everything is wired together. Run it with:  python main.py

The wiring has 4 steps: 1) create a session  2) create repositories  3) create the service
4) create the controller. Nothing to change in this file.
"""
from controllers.ticket_controller import TicketController
from db.database import create_session
from dtos.book_ticket_request_dto import BookTicketRequestDTO
from models.screen import Screen
from models.screen_status import ScreenStatus
from models.seat import Seat
from models.seat_status import SeatStatus
from models.seat_type import SeatType
from models.show import Show
from models.show_seat import ShowSeat
from models.user import User
from repositories.show_repository import ShowRepository
from repositories.show_seat_repository import ShowSeatRepository
from repositories.ticket_repository import TicketRepository
from repositories.user_repository import UserRepository
from services.ticket_service import TicketService


def main():
    session = create_session()

    show_seat_repository = ShowSeatRepository(session)
    ticket_repository = TicketRepository(session)
    user_repository = UserRepository(session)
    show_repository = ShowRepository(session)

    service = TicketService(show_seat_repository, ticket_repository, user_repository)
    controller = TicketController(service)

    # some data to play with: one show with 3 seats
    user = user_repository.save(User(name="Asha", email="asha@bms.com", password="secret"))
    screen = Screen(name="Screen 1", status=ScreenStatus.OPERATIONAL)
    screen.seats = [Seat(name=name, seat_type=SeatType.GOLD) for name in ("A1", "A2", "A3")]
    session.add(screen)
    session.commit()
    show = show_repository.save(Show(screen=screen))
    show_seats = show_seat_repository.save_all(
        [ShowSeat(show=show, seat=seat, status=SeatStatus.AVAILABLE) for seat in screen.seats])

    request = BookTicketRequestDTO(show_seat_ids=[show_seats[0].id, show_seats[1].id], user_id=user.id)
    response = controller.book_ticket(request)
    print("Status:", response.status)
    if response.ticket is not None:
        print("Ticket status:", response.ticket.status)
        print("Seats:", [seat.name for seat in response.ticket.seats])

    # the same seat again: it is blocked now, so this must fail
    response = controller.book_ticket(BookTicketRequestDTO(show_seat_ids=[show_seats[0].id], user_id=user.id))
    print("Booking a blocked seat again:", response.status)


if __name__ == "__main__":
    main()
