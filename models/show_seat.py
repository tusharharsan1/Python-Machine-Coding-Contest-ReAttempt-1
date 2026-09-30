from sqlalchemy import Column, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from models.base_model import BaseModel
from models.seat_status import SeatStatus


class ShowSeat(BaseModel):
    """One physical seat for one particular show, and whether it is AVAILABLE / BOOKED / BLOCKED."""
    __tablename__ = "show_seats"

    show_id = Column(Integer, ForeignKey("shows.id"))
    show = relationship("Show")
    seat_id = Column(Integer, ForeignKey("seats.id"))
    seat = relationship("Seat")
    status = Column(Enum(SeatStatus))
