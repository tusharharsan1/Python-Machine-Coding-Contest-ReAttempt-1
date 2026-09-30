from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from models.base_model import BaseModel


class Show(BaseModel):
    __tablename__ = "shows"

    start_time = Column(DateTime)
    end_time = Column(DateTime)
    screen_id = Column(Integer, ForeignKey("screens.id"))
    screen = relationship("Screen")
