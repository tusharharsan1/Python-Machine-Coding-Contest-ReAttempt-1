# Implement book ticket for Book My Show

## Problem Statement

You are building book my show. As a part of this system, you need to expose a functionality using which users can book tickets for a movie.

## Requirements
1. The request to book a ticket will contain the following things:
   * user_id - The user who is trying to book the ticket
   * List of show_seat_ids - The ids of the show_seats table which user is trying to book.
2. The system should check if the seats are available or not. If the seats are available, then the system should book the seats and return a ticket with the details of the seats booked and status of the ticket as `UNPAID` and the seats should be set to `BLOCKED` in the show_seats table. The ticket should also contain the show, the user and the time of booking.
3. Once the user pays for the ticket, the status of the ticket should be set to `BOOKED` and the seats should be set to `BOOKED` in the show_seats table. (This is out of scope for the current question)
4. Even if one of the seats is not available, then the system should not book any of the seats and raise an error saying "Seats are not available". Also, the ids of the unavailable seats should be part of the error message. A seat is not available if its status is `BLOCKED` or `BOOKED`.
5. Basic cases like invalid or non-existing user_id, invalid show_seat_ids (an id which does not exist, an empty list, or the same id sent twice) etc. should be handled. All the show seats of a request belong to the same show.
6. The system should be able to handle a large number of concurrent requests. If many users try to book the same seat at the same time, only one of them should get it. All the requests are handled by the same `TicketService` object, from many threads.

## Instructions (Expected Time: 30 - 35 minutes)

Follow these steps to complete the assignment:

### Step 1: Complete the Model (`models/` package)
- All the models except `Ticket` are already complete.
- Complete `ticket.py`: add the relationships to `show`, `user` and `seats` (a ticket has many seats). The in-between table for the seats is already written in `models/associations.py`.

### Step 2: Complete the Repository (`repositories/` package)
- `Repository` and all the repositories except `ShowSeatRepository` are already provided.
- In `ShowSeatRepository`, complete the method `find_show_seats_by_id_in(ids)` which returns the show seats whose id is in the list of ids.

### Step 3: Implement the Service Logic (`services/ticket_service.py`)
- The class skeleton is already provided with the repositories and a lock.
- Implement `book_ticket(show_seat_ids, user_id)` following the numbered `TODO` steps in the file:
  1. Run everything below inside the lock, so that two requests can never book the same seat.
  2. Validate the user exists (raise `InvalidUserException` if not found).
  3. Fetch the requested `ShowSeat`s using `find_show_seats_by_id_in(show_seat_ids)`. Verify that all requested seats were found (raise `InvalidShowSeatException` if not).
  4. Verify all seats have status `SeatStatus.AVAILABLE`. If any are booked or blocked, raise `SeatsNotAvailableException` with the ids of those seats.
  5. Mark all fetched show seats as `SeatStatus.BLOCKED`.
  6. Create a `Ticket` with the seats, show, current time, user and `TicketStatus.UNPAID`. Save it via `ticket_repository`.
  7. Return the saved ticket.

### Step 4: Wire the Controller (`controllers/ticket_controller.py`)
- Implement `book_ticket(request_dto)`:
  - Call `ticket_service.book_ticket(...)`.
  - Return `ResponseStatus.SUCCESS` with the ticket.
  - Catch any `Exception`, set `ResponseStatus.FAILURE`, and return (keep ticket `None`).
