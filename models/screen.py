from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from models.base_model import BaseModel
from models.screen_status import ScreenStatus


class Screen(BaseModel):
    __tablename__ = "screens"

    name = Column(String)
    status = Column(Enum(ScreenStatus))
    theatre_id = Column(Integer, ForeignKey("theatres.id"))
    theatre = relationship("Theatre", back_populates="screens")
    seats = relationship("Seat", back_populates="screen")
