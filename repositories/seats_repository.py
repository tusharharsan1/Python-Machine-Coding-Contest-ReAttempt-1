from sqlalchemy.orm import Session

from models.seat import Seat
from repositories.repository import Repository


class SeatsRepository(Repository[Seat]):
    def __init__(self, session: Session):
        super().__init__(session, Seat)
