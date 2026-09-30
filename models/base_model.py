from sqlalchemy import Column, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BaseModel(Base):
    # abstract = "not a table by itself"; every model that extends it just gets the id column
    __abstract__ = True

    id = Column(Integer, primary_key=True)
