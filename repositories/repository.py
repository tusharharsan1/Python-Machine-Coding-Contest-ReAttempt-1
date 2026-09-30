from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from models.base_model import BaseModel

T = TypeVar("T", bound=BaseModel)


class Repository(Generic[T]):
    """A generic helper used by every repository: it saves and reads rows of ONE model (table).

    `session` is our connection to the database, `model_class` tells which table we are working with
    (for example Ticket).
    """

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def save(self, item: T) -> T:
        """Saves one object and returns it.

        Everything that was changed in the session so far (for example a seat whose status you changed)
        is saved in the same go.
        """
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def save_all(self, items: List[T]) -> List[T]:
        """Saves many objects at once and returns them."""
        self.session.add_all(items)
        self.session.commit()
        return items

    def find_by_id(self, item_id: int) -> Optional[T]:
        """Returns the object with this id, or None if there is no such row."""
        return self.session.get(self.model_class, item_id)

    def find_all(self) -> List[T]:
        """Returns every row of this table."""
        return self.session.query(self.model_class).all()
