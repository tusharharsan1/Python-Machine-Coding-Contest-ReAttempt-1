# Importing every model here makes sure SQLAlchemy knows about all the tables
# before they are created. Do not remove any line.
from models.base_model import Base, BaseModel
from models.screen_status import ScreenStatus
from models.seat_status import SeatStatus
from models.seat_type import SeatType
from models.ticket_status import TicketStatus
from models.user import User
from models.movie import Movie
from models.city import City
from models.theatre import Theatre
from models.screen import Screen
from models.seat import Seat
from models.show import Show
from models.seat_type_show import SeatTypeShow
from models.show_seat import ShowSeat
from models.associations import ticket_seats
from models.ticket import Ticket
