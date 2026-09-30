from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from models.base_model import BaseModel


class City(BaseModel):
    __tablename__ = "cities"

    name = Column(String)
    theatres = relationship("Theatre", back_populates="city")
