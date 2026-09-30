from typing import List

from sqlalchemy.orm import Session

from models.show_seat import ShowSeat
from repositories.repository import Repository


class ShowSeatRepository(Repository[ShowSeat]):
    def __init__(self, session: Session):
        super().__init__(session, ShowSeat)

    def find_show_seats_by_id_in(self, ids: List[int]) -> List[ShowSeat]:
        """Returns all the show seats whose id is in the list `ids`."""
        return self.session.query(ShowSeat).filter(ShowSeat.id.in_(ids)).all()
