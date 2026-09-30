from sqlalchemy.orm import Session

from models.show import Show
from repositories.repository import Repository


class ShowRepository(Repository[Show]):
    def __init__(self, session: Session):
        super().__init__(session, Show)
