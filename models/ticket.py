from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from models.associations import ticket_seats
from models.base_model import BaseModel
from models.ticket_status import TicketStatus


class Ticket(BaseModel):
    """What the user gets after booking: which show, which user, which seats, when, and its status."""
    __tablename__ = "tickets"

    show_id = Column(Integer, ForeignKey("shows.id"))
    show = relationship("Show")

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

    # A ticket has many seats. `secondary` is the in-between table (see models/associations.py).
    seats = relationship("Seat", secondary=ticket_seats)

    time_of_booking = Column(DateTime)
    status = Column(Enum(TicketStatus))
