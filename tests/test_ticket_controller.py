import re
import threading
import time
import unittest
from datetime import datetime

from controllers.ticket_controller import TicketController
from db.database import create_session
from dtos.book_ticket_request_dto import BookTicketRequestDTO
from dtos.response_status import ResponseStatus
from exceptions.invalid_show_seat_exception import InvalidShowSeatException
from exceptions.invalid_user_exception import InvalidUserException
from exceptions.seats_not_available_exception import SeatsNotAvailableException
from models.screen import Screen
from models.screen_status import ScreenStatus
from models.seat import Seat
from models.seat_status import SeatStatus
from models.seat_type import SeatType
from models.show import Show
from models.show_seat import ShowSeat
from models.ticket import Ticket
from models.ticket_status import TicketStatus
from models.user import User
from repositories.show_repository import ShowRepository
from repositories.show_seat_repository import ShowSeatRepository
from repositories.ticket_repository import TicketRepository
from repositories.user_repository import UserRepository
from services.ticket_service import TicketService


class SlowShowSeatRepository(ShowSeatRepository):
    """Same as ShowSeatRepository, but it waits a little AFTER reading the seats.

    This makes the "two users read AVAILABLE at the same time" problem happen every time,
    if the service does not protect itself with the lock.
    """

    def find_show_seats_by_id_in(self, ids):
        show_seats = super().find_show_seats_by_id_in(ids)
        time.sleep(0.05)
        return show_seats


class TicketTestBase(unittest.TestCase):
    """Common setup used by every test class below.

    Before EVERY test we build a brand new, empty database and fill it with:
      users      : id 1 = Asha, id 2 = Bala, id 3 = Chitra
      screen     : 12 seats named A1 .. A12
      show 1     : one show seat per seat, ids 1 .. 12, all AVAILABLE
      show 2     : one show seat per seat, ids 13 .. 24, all AVAILABLE (another show on the same screen)
    """

    SEATS = 12
    slow_repository = False  # the concurrency tests switch this on

    def setUp(self):
        self.session = create_session()
        self.show_seat_repository = (SlowShowSeatRepository if self.slow_repository else ShowSeatRepository)(self.session)
        self.ticket_repository = TicketRepository(self.session)
        self.user_repository = UserRepository(self.session)
        self.show_repository = ShowRepository(self.session)

        self.service = TicketService(self.show_seat_repository, self.ticket_repository, self.user_repository)
        self.controller = TicketController(self.service)

        self.asha = self._add_user("Asha")
        self.bala = self._add_user("Bala")
        self.chitra = self._add_user("Chitra")

        screen = Screen(name="Screen 1", status=ScreenStatus.OPERATIONAL)
        screen.seats = [Seat(name=f"A{i}", seat_type=SeatType.GOLD) for i in range(1, self.SEATS + 1)]
        self.session.add(screen)
        self.session.commit()
        self.screen = screen

        self.show_one = self.show_repository.save(Show(screen=screen))
        self.show_two = self.show_repository.save(Show(screen=screen))
        self.show_seats_one = self._add_show_seats(self.show_one)   # ids 1 .. 12
        self.show_seats_two = self._add_show_seats(self.show_two)   # ids 13 .. 24

    def tearDown(self):
        engine = self.session.get_bind()
        self.session.close()
        engine.dispose()

    # ---------- helpers to build data ----------
    def _add_user(self, name):
        return self.user_repository.save(User(name=name, email=name.lower() + "@bms.com", password="secret"))

    def _add_show_seats(self, show):
        show_seats = [ShowSeat(show=show, seat=seat, status=SeatStatus.AVAILABLE) for seat in self.screen.seats]
        return self.show_seat_repository.save_all(show_seats)

    def _set_status(self, show_seat_ids, status):
        for show_seat_id in show_seat_ids:
            self.show_seat_repository.find_by_id(show_seat_id).status = status
        self.session.commit()

    def _ids(self, show_seats):
        return [show_seat.id for show_seat in show_seats]

    # ---------- helpers to call the code ----------
    def _book(self, show_seat_ids, user=None):
        """Calls the controller (as `user`, Chitra by default)."""
        user_id = (user or self.chitra).id
        return self.controller.book_ticket(BookTicketRequestDTO(show_seat_ids=show_seat_ids, user_id=user_id))

    # ---------- helpers to look at the database ----------
    def _status_of(self, show_seat_id):
        self.session.expire_all()
        return self.show_seat_repository.find_by_id(show_seat_id).status

    def _statuses(self):
        """{show seat id: status} of every show seat."""
        self.session.expire_all()
        return {show_seat.id: show_seat.status for show_seat in self.show_seat_repository.find_all()}

    def _ticket_count(self):
        self.session.expire_all()
        return self.session.query(Ticket).count()

    def assert_success(self, response):
        self.assertEqual(ResponseStatus.SUCCESS, response.status)
        self.assertIsNotNone(response.ticket)

    def assert_failure_and_nothing_changed(self, response, statuses_before):
        """A failed booking: FAILURE, no ticket in the response, no ticket saved, no seat changed."""
        self.assertEqual(ResponseStatus.FAILURE, response.status)
        self.assertIsNone(response.ticket)
        self.assertEqual(0, self._ticket_count(), "no ticket should have been saved")
        self.assertEqual(statuses_before, self._statuses(), "no seat should have been changed")


# ======================================================================================
# 1. The Ticket model and the repository query (each can earn marks on its own)
# ======================================================================================
class ModelAndRepositoryTest(TicketTestBase):

    def _saved_ticket(self, seats, user=None, show=None, status=TicketStatus.UNPAID):
        ticket = Ticket()
        ticket.seats = seats
        ticket.show = show or self.show_one
        ticket.user = user or self.asha
        ticket.time_of_booking = datetime(2030, 5, 17, 18, 30)
        ticket.status = status
        return self.ticket_repository.save(ticket)

    def _reload(self, ticket_id):
        """Forgets every object in memory, so the ticket is really read again from the database."""
        self.session.expunge_all()
        return self.ticket_repository.find_by_id(ticket_id)

    def test_ticket_keeps_its_show_user_status_and_time(self):
        show_id, user_id = self.show_two.id, self.bala.id
        saved = self._saved_ticket([self.screen.seats[0]], user=self.bala, show=self.show_two)
        loaded = self._reload(saved.id)
        self.assertEqual(show_id, loaded.show.id)
        self.assertEqual(user_id, loaded.user.id)
        self.assertEqual(TicketStatus.UNPAID, loaded.status)
        self.assertEqual(datetime(2030, 5, 17, 18, 30), loaded.time_of_booking)

    def test_ticket_keeps_all_its_seats(self):
        seat_ids = sorted(seat.id for seat in self.screen.seats[:4])
        saved = self._saved_ticket(self.screen.seats[:4])
        loaded = self._reload(saved.id)
        self.assertEqual(seat_ids, sorted(seat.id for seat in loaded.seats))

    def test_ticket_seats_are_seat_objects(self):
        saved = self._saved_ticket([self.screen.seats[0], self.screen.seats[1]])
        loaded = self._reload(saved.id)
        self.assertEqual(2, len(loaded.seats))
        for seat in loaded.seats:
            self.assertIsInstance(seat, Seat)
        self.assertEqual({"A1", "A2"}, {seat.name for seat in loaded.seats})

    def test_ticket_status_can_be_any_ticket_status(self):
        saved = self._saved_ticket([self.screen.seats[0]], status=TicketStatus.CANCELLED)
        loaded = self._reload(saved.id)
        self.assertEqual(TicketStatus.CANCELLED, loaded.status)
        self.assertEqual(1, len(loaded.seats))

    def test_the_same_seat_can_be_on_two_tickets_over_time(self):
        seat_id = self.screen.seats[0].id
        first = self._saved_ticket([self.screen.seats[0]], status=TicketStatus.CANCELLED)
        second = self._saved_ticket([self.screen.seats[0]], user=self.bala)
        first_id, second_id = first.id, second.id
        for ticket_id in (first_id, second_id):
            self.assertEqual([seat_id], [s.id for s in self._reload(ticket_id).seats])

    def test_a_ticket_without_seats_can_be_saved(self):
        show_id = self.show_one.id
        saved = self._saved_ticket([])
        loaded = self._reload(saved.id)
        self.assertEqual([], loaded.seats)
        self.assertEqual(show_id, loaded.show.id)

    def test_find_show_seats_by_id_in_returns_the_requested_show_seats(self):
        result = self.show_seat_repository.find_show_seats_by_id_in([2, 5, 7])
        self.assertEqual([2, 5, 7], sorted(self._ids(result)))

    def test_find_show_seats_by_id_in_returns_show_seat_objects(self):
        result = self.show_seat_repository.find_show_seats_by_id_in([1])
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], ShowSeat)
        self.assertEqual(SeatStatus.AVAILABLE, result[0].status)

    def test_find_show_seats_by_id_in_leaves_out_unknown_ids(self):
        result = self.show_seat_repository.find_show_seats_by_id_in([3, 999, 4])
        self.assertEqual([3, 4], sorted(self._ids(result)))

    def test_find_show_seats_by_id_in_with_only_unknown_ids_returns_empty_list(self):
        self.assertEqual([], self.show_seat_repository.find_show_seats_by_id_in([998, 999]))

    def test_find_show_seats_by_id_in_with_an_empty_list_returns_empty_list(self):
        self.assertEqual([], self.show_seat_repository.find_show_seats_by_id_in([]))

    def test_find_show_seats_by_id_in_returns_a_repeated_id_only_once(self):
        result = self.show_seat_repository.find_show_seats_by_id_in([3, 3])
        self.assertEqual([3], self._ids(result))

    def test_find_show_seats_by_id_in_works_for_the_other_show_too(self):
        result = self.show_seat_repository.find_show_seats_by_id_in([13, 24])
        self.assertEqual({self.show_two.id}, {show_seat.show.id for show_seat in result})


# ======================================================================================
# 2. The controller alone: a fake service lets us check ONLY what the controller does
# ======================================================================================
class FakeTicketService:
    """Pretends to be TicketService. Remembers how it was called."""

    def __init__(self, ticket_to_return=None, error_to_raise=None):
        self.ticket_to_return = ticket_to_return
        self.error_to_raise = error_to_raise
        self.calls = []

    def book_ticket(self, show_seat_ids, user_id):
        self.calls.append((show_seat_ids, user_id))
        if self.error_to_raise is not None:
            raise self.error_to_raise
        return self.ticket_to_return


class ControllerOnlyTest(unittest.TestCase):

    def test_success_returns_the_ticket_from_the_service_and_success_status(self):
        ticket = Ticket()
        response = TicketController(FakeTicketService(ticket_to_return=ticket)).book_ticket(
            BookTicketRequestDTO(show_seat_ids=[1, 2], user_id=9))
        self.assertEqual(ResponseStatus.SUCCESS, response.status)
        self.assertIs(ticket, response.ticket)

    def test_controller_passes_the_seat_ids_and_the_user_id_to_the_right_parameters(self):
        service = FakeTicketService(ticket_to_return=Ticket())
        TicketController(service).book_ticket(BookTicketRequestDTO(show_seat_ids=[4, 5, 6], user_id=77))
        self.assertEqual([([4, 5, 6], 77)], service.calls)

    def test_controller_passes_other_values_too(self):
        service = FakeTicketService(ticket_to_return=Ticket())
        TicketController(service).book_ticket(BookTicketRequestDTO(show_seat_ids=[10], user_id=3))
        self.assertEqual([([10], 3)], service.calls)

    def test_any_exception_gives_failure_and_no_ticket(self):
        for error in (InvalidUserException("x"), SeatsNotAvailableException("x"), RuntimeError("other")):
            with self.subTest(error=type(error).__name__):
                response = TicketController(FakeTicketService(error_to_raise=error)).book_ticket(
                    BookTicketRequestDTO(show_seat_ids=[1], user_id=1))
                self.assertEqual(ResponseStatus.FAILURE, response.status)
                self.assertIsNone(response.ticket)

    def test_the_controller_does_not_raise_when_the_service_fails(self):
        controller = TicketController(FakeTicketService(error_to_raise=ValueError("boom")))
        try:
            response = controller.book_ticket(BookTicketRequestDTO(show_seat_ids=[1], user_id=1))
        except Exception as error:
            self.fail(f"The controller must catch the exception, but it raised {error!r}")
        self.assertEqual(ResponseStatus.FAILURE, response.status)


# ======================================================================================
# 3. The whole flow through the controller
# ======================================================================================
class TicketControllerTest(TicketTestBase):

    # ---------- a successful booking ----------
    def test_booking_available_seats_gives_success_and_a_ticket(self):
        self.assert_success(self._book([1, 2]))

    def test_ticket_is_unpaid(self):
        self.assertEqual(TicketStatus.UNPAID, self._book([1, 2]).ticket.status)

    def test_ticket_belongs_to_the_user_who_booked(self):
        self.assertEqual(self.bala.id, self._book([1], user=self.bala).ticket.user.id)
        self.assertEqual(self.asha.id, self._book([2], user=self.asha).ticket.user.id)

    def test_ticket_is_for_the_show_of_the_seats(self):
        self.assertEqual(self.show_one.id, self._book([1, 2]).ticket.show.id)
        self.assertEqual(self.show_two.id, self._book([13, 14]).ticket.show.id)

    def test_ticket_contains_the_seats_which_were_booked(self):
        ticket = self._book([2, 4, 6]).ticket
        self.assertEqual(["A2", "A4", "A6"], sorted(seat.name for seat in ticket.seats))
        self.assertEqual(3, len(ticket.seats))

    def test_ticket_seats_are_the_seats_of_the_show_seats(self):
        ticket = self._book([3]).ticket
        self.assertEqual([self.show_seats_one[2].seat.id], [seat.id for seat in ticket.seats])

    def test_ticket_time_of_booking_is_now(self):
        before = datetime.now()
        ticket = self._book([1]).ticket
        after = datetime.now()
        self.assertIsNotNone(ticket.time_of_booking)
        self.assertTrue(before <= ticket.time_of_booking <= after)

    def test_ticket_is_saved_in_the_database(self):
        ticket = self._book([1, 2]).ticket
        self.assertIsNotNone(ticket.id)
        self.assertEqual(1, self._ticket_count())
        self.assertEqual(ticket.id, self.ticket_repository.find_all()[0].id)

    def test_booked_seats_become_blocked_in_the_database(self):
        self._book([1, 2, 3])
        for show_seat_id in (1, 2, 3):
            self.assertEqual(SeatStatus.BLOCKED, self._status_of(show_seat_id))

    def test_the_seats_are_blocked_not_booked(self):
        self.assert_success(self._book([1]))
        self.assertEqual(SeatStatus.BLOCKED, self._status_of(1))
        self.assertNotEqual(SeatStatus.BOOKED, self._status_of(1))

    def test_other_seats_of_the_same_show_stay_available(self):
        self.assert_success(self._book([1, 2]))
        for show_seat_id in range(3, 13):
            self.assertEqual(SeatStatus.AVAILABLE, self._status_of(show_seat_id))

    def test_the_same_seats_of_another_show_stay_available(self):
        self.assert_success(self._book([1, 2]))
        for show_seat_id in (13, 14):
            self.assertEqual(SeatStatus.AVAILABLE, self._status_of(show_seat_id))

    def test_booking_a_single_seat(self):
        response = self._book([7])
        self.assert_success(response)
        self.assertEqual(1, len(response.ticket.seats))
        self.assertEqual(SeatStatus.BLOCKED, self._status_of(7))

    def test_booking_all_the_seats_of_the_show(self):
        response = self._book(list(range(1, 13)))
        self.assert_success(response)
        self.assertEqual(12, len(response.ticket.seats))
        self.assertEqual({SeatStatus.BLOCKED}, {self._statuses()[i] for i in range(1, 13)})

    def test_the_order_of_the_ids_does_not_matter(self):
        response = self._book([5, 1, 3])
        self.assert_success(response)
        self.assertEqual(["A1", "A3", "A5"], sorted(seat.name for seat in response.ticket.seats))

    def test_two_users_can_book_different_seats(self):
        first = self._book([1, 2], user=self.asha)
        second = self._book([3, 4], user=self.bala)
        self.assert_success(first)
        self.assert_success(second)
        self.assertNotEqual(first.ticket.id, second.ticket.id)
        self.assertEqual(2, self._ticket_count())

    def test_the_same_user_can_book_twice(self):
        self.assert_success(self._book([1]))
        self.assert_success(self._book([2]))
        self.assertEqual(2, self._ticket_count())

    def test_a_seat_can_be_booked_in_two_different_shows(self):
        self.assert_success(self._book([1]))
        self.assert_success(self._book([13]))
        self.assertEqual(2, self._ticket_count())

    def test_seats_that_are_available_after_a_failed_try_can_be_booked(self):
        self._set_status([2], SeatStatus.BLOCKED)
        self.assertEqual(ResponseStatus.FAILURE, self._book([1, 2]).status)
        self.assert_success(self._book([1, 3]))
        self.assertEqual(SeatStatus.BLOCKED, self._status_of(1))

    # ---------- unavailable seats ----------
    def test_a_blocked_seat_cannot_be_booked(self):
        self._set_status([3], SeatStatus.BLOCKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([3]), before)

    def test_a_booked_seat_cannot_be_booked(self):
        self._set_status([3], SeatStatus.BOOKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([3]), before)

    def test_if_one_seat_is_blocked_none_of_the_seats_is_booked(self):
        self._set_status([3], SeatStatus.BLOCKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 3, 4]), before)
        self.assertEqual(SeatStatus.AVAILABLE, self._status_of(1))
        self.assertEqual(SeatStatus.AVAILABLE, self._status_of(4))

    def test_if_the_first_seat_is_unavailable_the_others_are_not_booked_either(self):
        self._set_status([1], SeatStatus.BOOKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 3]), before)

    def test_if_the_last_seat_is_unavailable_the_others_are_not_booked_either(self):
        self._set_status([3], SeatStatus.BOOKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 3]), before)

    def test_several_unavailable_seats_fail_the_whole_request(self):
        self._set_status([2], SeatStatus.BLOCKED)
        self._set_status([4], SeatStatus.BOOKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 3, 4]), before)

    def test_all_seats_unavailable(self):
        self._set_status([1, 2], SeatStatus.BLOCKED)
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2]), before)

    def test_a_seat_cannot_be_booked_twice(self):
        first = self._book([5], user=self.asha)
        self.assert_success(first)
        second = self._book([5], user=self.bala)
        self.assertEqual(ResponseStatus.FAILURE, second.status)
        self.assertIsNone(second.ticket)
        self.assertEqual(1, self._ticket_count())
        self.assertEqual(self.asha.id, self.ticket_repository.find_all()[0].user.id)

    def test_partly_overlapping_second_request_fails_and_keeps_its_free_seat(self):
        self.assert_success(self._book([1, 2]))
        second = self._book([2, 3])
        self.assertEqual(ResponseStatus.FAILURE, second.status)
        self.assertEqual(SeatStatus.AVAILABLE, self._status_of(3))
        self.assertEqual(1, self._ticket_count())

    # ---------- invalid requests ----------
    def test_unknown_user_fails(self):
        before = self._statuses()
        response = self.controller.book_ticket(BookTicketRequestDTO(show_seat_ids=[1, 2], user_id=999))
        self.assert_failure_and_nothing_changed(response, before)

    def test_user_id_zero_and_negative_fail(self):
        before = self._statuses()
        for user_id in (0, -1):
            with self.subTest(user_id=user_id):
                response = self.controller.book_ticket(BookTicketRequestDTO(show_seat_ids=[1], user_id=user_id))
                self.assert_failure_and_nothing_changed(response, before)

    def test_unknown_show_seat_id_fails(self):
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([999]), before)

    def test_one_unknown_show_seat_id_among_valid_ones_fails_and_books_nothing(self):
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 999]), before)

    def test_show_seat_id_zero_and_negative_fail(self):
        before = self._statuses()
        for show_seat_id in (0, -4):
            with self.subTest(show_seat_id=show_seat_id):
                self.assert_failure_and_nothing_changed(self._book([show_seat_id]), before)

    def test_empty_list_of_show_seats_fails(self):
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([]), before)

    def test_the_same_show_seat_id_twice_fails(self):
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 1]), before)

    def test_a_repeated_id_among_other_ids_fails(self):
        before = self._statuses()
        self.assert_failure_and_nothing_changed(self._book([1, 2, 1]), before)

    def test_a_failure_can_be_followed_by_a_success(self):
        self.assertEqual(ResponseStatus.FAILURE, self._book([999]).status)
        self.assert_success(self._book([1, 2]))

    def test_a_failure_after_a_success_does_not_change_the_first_ticket(self):
        ticket = self._book([1, 2]).ticket
        self.assertEqual(ResponseStatus.FAILURE, self._book([2, 3]).status)
        self.session.expire_all()
        saved = self.ticket_repository.find_by_id(ticket.id)
        self.assertEqual(TicketStatus.UNPAID, saved.status)
        self.assertEqual(2, len(saved.seats))


# ======================================================================================
# 4. The service: which exception is raised, and in which order things are checked
# ======================================================================================
class TicketServiceExceptionTest(TicketTestBase):

    def test_valid_request_returns_a_ticket(self):
        ticket = self.service.book_ticket([1, 2], self.asha.id)
        self.assertIsInstance(ticket, Ticket)
        self.assertIsNotNone(ticket.id)

    def test_unknown_user_raises_invalid_user(self):
        with self.assertRaises(InvalidUserException):
            self.service.book_ticket([1], 999)

    def test_unknown_show_seat_raises_invalid_show_seat(self):
        with self.assertRaises(InvalidShowSeatException):
            self.service.book_ticket([1, 999], self.asha.id)

    def test_empty_list_raises_invalid_show_seat(self):
        with self.assertRaises(InvalidShowSeatException):
            self.service.book_ticket([], self.asha.id)

    def test_repeated_id_raises_invalid_show_seat(self):
        with self.assertRaises(InvalidShowSeatException):
            self.service.book_ticket([2, 2], self.asha.id)

    def test_blocked_seat_raises_seats_not_available(self):
        self._set_status([2], SeatStatus.BLOCKED)
        with self.assertRaises(SeatsNotAvailableException):
            self.service.book_ticket([1, 2], self.asha.id)

    def test_booked_seat_raises_seats_not_available(self):
        self._set_status([2], SeatStatus.BOOKED)
        with self.assertRaises(SeatsNotAvailableException):
            self.service.book_ticket([2], self.asha.id)

    def test_the_messages_are_not_empty(self):
        self._set_status([2], SeatStatus.BLOCKED)
        for args, error in (((([1], 999)), InvalidUserException),
                            (([999], self.asha.id), InvalidShowSeatException),
                            (([2], self.asha.id), SeatsNotAvailableException)):
            with self.subTest(error=error.__name__):
                with self.assertRaises(error) as context:
                    self.service.book_ticket(*args)
                self.assertTrue(str(context.exception).strip())

    # ---------- the message of SeatsNotAvailableException ----------
    def test_message_says_that_seats_are_not_available(self):
        self._set_status([4], SeatStatus.BLOCKED)
        with self.assertRaises(SeatsNotAvailableException) as context:
            self.service.book_ticket([4], self.asha.id)
        self.assertIn("Seats are not available", str(context.exception))

    def test_message_contains_the_id_of_the_unavailable_seat(self):
        self._set_status([4], SeatStatus.BLOCKED)
        with self.assertRaises(SeatsNotAvailableException) as context:
            self.service.book_ticket([3, 4, 5], self.asha.id)
        self.assertRegex(str(context.exception), r"\b4\b")

    def test_message_contains_the_ids_of_all_the_unavailable_seats(self):
        self._set_status([2], SeatStatus.BLOCKED)
        self._set_status([5], SeatStatus.BOOKED)
        with self.assertRaises(SeatsNotAvailableException) as context:
            self.service.book_ticket([1, 2, 3, 5], self.asha.id)
        message = str(context.exception)
        self.assertRegex(message, r"\b2\b")
        self.assertRegex(message, r"\b5\b")

    def test_message_does_not_contain_the_ids_of_the_available_seats(self):
        self._set_status([2], SeatStatus.BLOCKED)
        with self.assertRaises(SeatsNotAvailableException) as context:
            self.service.book_ticket([1, 2, 3], self.asha.id)
        message = str(context.exception)
        self.assertNotRegex(message, r"\b1\b")
        self.assertNotRegex(message, r"\b3\b")

    def test_nothing_is_saved_when_the_service_raises(self):
        self._set_status([2], SeatStatus.BLOCKED)
        before = self._statuses()
        with self.assertRaises(SeatsNotAvailableException):
            self.service.book_ticket([1, 2, 3], self.asha.id)
        self.assertEqual(before, self._statuses())
        self.assertEqual(0, self._ticket_count())

    # ---------- order of the checks: only the FIRST problem is reported ----------
    def test_invalid_user_is_reported_before_invalid_show_seats(self):
        with self.assertRaises(InvalidUserException):
            self.service.book_ticket([999], 999)

    def test_invalid_user_is_reported_before_unavailable_seats(self):
        self._set_status([1], SeatStatus.BLOCKED)
        with self.assertRaises(InvalidUserException):
            self.service.book_ticket([1], 999)

    def test_invalid_show_seats_are_reported_before_unavailable_seats(self):
        self._set_status([1], SeatStatus.BLOCKED)
        with self.assertRaises(InvalidShowSeatException):
            self.service.book_ticket([1, 999], self.asha.id)


# ======================================================================================
# 5. Many users at the same time (requirement 6)
# ======================================================================================
# Every scenario is run in a SEPARATE program (a child process): several threads that use the database
# without a proper lock can even crash Python. This way a crash only fails that one test.
# Each scenario is a list of "rounds". A round = requests that start at the same moment, one thread each.
# A request = (list of show seat ids, name of the user).
SCENARIOS = {
    "same_seat_two_users": [[([1], "asha"), ([1], "bala")]],
    "same_seats_nine_users": [[([1, 2], name) for name in ("asha", "bala", "chitra") * 3]],
    "different_seats": [[([1], "asha"), ([2], "bala"), ([3], "chitra"), ([4, 5], "asha")]],
    "overlapping_seats": [[([1, 2], "asha"), ([2, 3], "bala")]],
    "same_seat_two_shows": [[([1], "asha"), ([13], "bala")]],
    "mixed": [[([1], "asha"), ([1], "bala"), ([1], "chitra"), ([2], "asha"), ([3], "bala")]],
    "three_races_in_a_row": [[([6], "asha"), ([6], "bala")], [([7], "asha"), ([7], "bala")],
                             [([8], "asha"), ([8], "bala")]],
}


def run_scenario(name):
    """Runs one scenario and prints the result as JSON. Called in the child process."""
    import json
    case = ConcurrencyTest()
    case.setUp()
    users = {"asha": case.asha.id, "bala": case.bala.id, "chitra": case.chitra.id}
    rounds = []
    for requests in SCENARIOS[name]:
        dtos = [BookTicketRequestDTO(show_seat_ids=ids, user_id=users[user]) for ids, user in requests]
        responses = [None] * len(dtos)
        start_together = threading.Barrier(len(dtos))

        def worker(index):
            start_together.wait()
            responses[index] = case.controller.book_ticket(dtos[index])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(dtos))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        rounds.append([{"success": r.status == ResponseStatus.SUCCESS,
                        "has_ticket": r.ticket is not None,
                        "failed": r.status == ResponseStatus.FAILURE,
                        "ticket_id": r.ticket.id if r.ticket is not None else None} for r in responses])
    print(json.dumps({
        "rounds": rounds,
        "ticket_ids_in_db": [t.id for t in case.ticket_repository.find_all()],
        "statuses": {str(k): v.name for k, v in case._statuses().items()},
    }))
    case.tearDown()


class ConcurrencyTest(TicketTestBase):
    """Every thread calls the SAME controller/service, like real users of one system.

    The repository waits a little after reading the seats (see SlowShowSeatRepository), so if the service
    does not protect the "read seats, check, block" part properly, several users get the same seat.
    """
    slow_repository = True

    def _run(self, name):
        import json
        import os
        import subprocess
        import sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            done = subprocess.run(
                [sys.executable, "-c", f"from tests.test_ticket_controller import run_scenario; run_scenario({name!r})"],
                cwd=root, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            self.fail("the users did not finish in 60 seconds (deadlock?)")
        if done.returncode != 0:
            self.fail("the program crashed while many users were booking at the same time. Is the lock "
                      "shared by all the requests, and are ALL the steps inside it?\n" + done.stderr[-500:])
        return json.loads(done.stdout.strip().splitlines()[-1])

    def _successes(self, round_results):
        return [r for r in round_results if r["success"]]

    def test_two_users_booking_the_same_seat_only_one_gets_it(self):
        result = self._run("same_seat_two_users")
        self.assertEqual(1, len(self._successes(result["rounds"][0])))
        self.assertEqual(1, len(result["ticket_ids_in_db"]))
        self.assertEqual("BLOCKED", result["statuses"]["1"])

    def test_the_user_who_did_not_get_the_seat_gets_a_failure_and_no_ticket(self):
        result = self._run("same_seat_two_users")
        losers = [r for r in result["rounds"][0] if not r["success"]]
        self.assertEqual(1, len(losers))
        self.assertTrue(losers[0]["failed"])
        self.assertFalse(losers[0]["has_ticket"])

    def test_the_winner_ticket_is_the_only_ticket_in_the_database(self):
        result = self._run("same_seat_two_users")
        winner = self._successes(result["rounds"][0])[0]
        self.assertEqual([winner["ticket_id"]], result["ticket_ids_in_db"])

    def test_many_users_booking_the_same_seats_only_one_gets_them(self):
        result = self._run("same_seats_nine_users")
        self.assertEqual(1, len(self._successes(result["rounds"][0])))
        self.assertEqual(1, len(result["ticket_ids_in_db"]))
        self.assertEqual("BLOCKED", result["statuses"]["1"])
        self.assertEqual("BLOCKED", result["statuses"]["2"])

    def test_users_booking_different_seats_all_get_them(self):
        result = self._run("different_seats")
        self.assertEqual(4, len(self._successes(result["rounds"][0])))
        self.assertEqual(4, len(result["ticket_ids_in_db"]))
        for show_seat_id in "12345":
            self.assertEqual("BLOCKED", result["statuses"][show_seat_id])

    def test_overlapping_requests_only_one_wins_and_the_other_books_nothing(self):
        result = self._run("overlapping_seats")
        first, second = result["rounds"][0]
        self.assertEqual(1, len(self._successes(result["rounds"][0])))
        self.assertEqual(1, len(result["ticket_ids_in_db"]))
        # the request which lost must not have blocked its own free seat
        loser_free_seat = "3" if first["success"] else "1"
        self.assertEqual("AVAILABLE", result["statuses"][loser_free_seat])
        self.assertEqual("BLOCKED", result["statuses"]["2"])

    def test_the_same_seat_in_two_different_shows_can_be_booked_at_the_same_time(self):
        result = self._run("same_seat_two_shows")
        self.assertEqual(2, len(self._successes(result["rounds"][0])))
        self.assertEqual(2, len(result["ticket_ids_in_db"]))

    def test_a_mix_of_same_and_different_seats(self):
        result = self._run("mixed")
        self.assertEqual(3, len(self._successes(result["rounds"][0])))
        self.assertEqual(3, len(result["ticket_ids_in_db"]))
        for show_seat_id in "123":
            self.assertEqual("BLOCKED", result["statuses"][show_seat_id])

    def test_the_lock_is_shared_by_all_requests_of_the_service(self):
        # a lock created inside book_ticket() would not stop anybody, this repeats the race three times
        result = self._run("three_races_in_a_row")
        for round_number, round_results in enumerate(result["rounds"]):
            self.assertEqual(1, len(self._successes(round_results)), f"round {round_number}")
        self.assertEqual(3, len(result["ticket_ids_in_db"]))


if __name__ == "__main__":
    unittest.main()
