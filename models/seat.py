from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from models.base_model import BaseModel
from models.seat_type import SeatType


class Seat(BaseModel):
    __tablename__ = "seats"

    name = Column(String)
    seat_type = Column(Enum(SeatType))
    screen_id = Column(Integer, ForeignKey("screens.id"))
    screen = relationship("Screen", back_populates="seats")
