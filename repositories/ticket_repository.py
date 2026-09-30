from sqlalchemy.orm import Session

from models.ticket import Ticket
from repositories.repository import Repository


class TicketRepository(Repository[Ticket]):
    def __init__(self, session: Session):
        super().__init__(session, Ticket)
