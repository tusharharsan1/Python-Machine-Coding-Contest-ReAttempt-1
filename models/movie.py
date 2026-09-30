from sqlalchemy import Column, String

from models.base_model import BaseModel


class Movie(BaseModel):
    __tablename__ = "movies"

    name = Column(String)
    description = Column(String)
