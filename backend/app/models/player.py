"""Player model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class Player(Base):
    """Player model representing football players in the system."""
    
    __tablename__ = 'players'

    player_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    date_of_birth = Column(Date)
    nationality = Column(String(50))
    position = Column(String(20), nullable=True)
    team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=True)

    # Relationships
    team = relationship("Team", back_populates="players")
    injuries = relationship("Injury", back_populates="player", cascade="all, delete-orphan")
    transfers = relationship("TransferStatus", back_populates="player", cascade="all, delete-orphan")
    news_updates = relationship("NewsUpdate", back_populates="player")

    def __repr__(self):
        return f"<Player(name='{self.name}', position='{self.position}')>"
