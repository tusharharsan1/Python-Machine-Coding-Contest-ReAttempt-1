from sqlalchemy.orm import Session

from models.user import User
from repositories.repository import Repository


class UserRepository(Repository[User]):
    def __init__(self, session: Session):
        super().__init__(session, User)
