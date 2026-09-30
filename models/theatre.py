from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from models.base_model import BaseModel


class Theatre(BaseModel):
    __tablename__ = "theatres"

    name = Column(String)
    address = Column(String)
    city_id = Column(Integer, ForeignKey("cities.id"))
    city = relationship("City", back_populates="theatres")
    screens = relationship("Screen", back_populates="theatre")
