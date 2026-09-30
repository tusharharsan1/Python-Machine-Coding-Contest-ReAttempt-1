from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  (makes sure every table is known before we create them)
from models.base_model import Base


def create_session() -> Session:
    """Creates a brand new, empty, in-memory SQLite database (with all tables) and returns a session for it.

    "In memory" means the data disappears when the program ends.
    The two extra settings let several threads use the same in-memory database.
    You do not need to change this file.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)
