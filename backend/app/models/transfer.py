"""Transfer model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class TransferStatus(Base):
    """TransferStatus model representing player transfers and rumors."""
    
    __tablename__ = 'transfer_status'

    transfer_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), nullable=False)
    status = Column(String(20), nullable=False)  # Rumored/In Progress/Completed
    last_update = Column(Date, nullable=False)
    destination_club = Column(String(100))
    transfer_fee = Column(Float)  # in millions of euros

    # Relationships
    player = relationship("Player", back_populates="transfers")

    def __repr__(self):
        return f"<TransferStatus(player_id={self.player_id}, status='{self.status}', destination='{self.destination_club}')>"
