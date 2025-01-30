"""Injury model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class Injury(Base):
    """Injury model representing player injuries in the system."""
    
    __tablename__ = 'injuries'

    injury_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), nullable=False)
    description = Column(String(500))
    injury_date = Column(Date, nullable=False)
    recovery_estimated = Column(Date)
    severity = Column(String(20))  # E.g., Minor, Moderate, Severe

    # Relationships
    player = relationship("Player", back_populates="injuries")

    def __repr__(self):
        return f"<Injury(player_id={self.player_id}, severity='{self.severity}')>"
