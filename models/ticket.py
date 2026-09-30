from sqlalchemy import Column, DateTime, Enum

from models.base_model import BaseModel
from models.ticket_status import TicketStatus

# TODO: Complete this model. It is the "tickets" table.
#
# A Ticket is what the user gets after booking: which show, which user, which seats, when, and its status.
#
# Steps (add the missing imports at the top of the file):
#   from sqlalchemy import ForeignKey, Integer
#   from sqlalchemy.orm import relationship
#   from models.associations import ticket_seats
#
# 1. Add a foreign key column   show_id   pointing to "shows.id"
#    and   show = relationship("Show")
# 2. Add a foreign key column   user_id   pointing to "users.id"
#    and   user = relationship("User")
# 3. Add   seats = relationship("Seat", secondary=ticket_seats)
#    A ticket has many seats. `secondary=` tells SQLAlchemy which in-between table connects the two sides
#    (it is already written for you in models/associations.py).
#
# Hint: models/show_seat.py already has a foreign key with a relationship, and
#       models/associations.py shows the table that `secondary` points to.


class Ticket(BaseModel):
    __tablename__ = "tickets"  # already given, keep it

    time_of_booking = Column(DateTime)
    status = Column(Enum(TicketStatus))
