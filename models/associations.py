from sqlalchemy import Column, ForeignKey, Integer, Table

from models.base_model import Base

# A ticket has many seats and, over time, a seat can be on many tickets (many-to-many).
# A many-to-many relationship needs a table of its own in between:
# every row of this table says "this seat is part of this ticket".
ticket_seats = Table(
    "ticket_seats",
    Base.metadata,
    Column("ticket_id", Integer, ForeignKey("tickets.id"), primary_key=True),
    Column("seat_id", Integer, ForeignKey("seats.id"), primary_key=True),
)
