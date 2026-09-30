from sqlalchemy import Column, String

from models.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name = Column(String)
    email = Column(String)
    password = Column(String)
