from dtos.book_ticket_request_dto import BookTicketRequestDTO
from dtos.book_ticket_response_dto import BookTicketResponseDTO
from dtos.response_status import ResponseStatus
from services.ticket_service import TicketService


class TicketController:
    def __init__(self, ticket_service: TicketService):
        self.ticket_service = ticket_service

    def book_ticket(self, request_dto: BookTicketRequestDTO) -> BookTicketResponseDTO:
        response_dto = BookTicketResponseDTO()
        try:
            # TODO: 1. Call self.ticket_service.book_ticket(request_dto.show_seat_ids, request_dto.user_id)
            #       2. Put the Ticket that comes back in response_dto.ticket
            #       3. Set response_dto.status = ResponseStatus.SUCCESS
            pass
        except Exception:
            # If ANY exception happens (invalid user, seat already blocked, ...), the status is FAILURE
            # and the ticket must stay None.
            response_dto.status = ResponseStatus.FAILURE
        return response_dto
