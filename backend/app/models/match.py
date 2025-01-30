"""Match model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class Match(Base):
    """Match model representing football matches in the system."""
    
    __tablename__ = 'matches'

    match_id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    match_date = Column(Date, nullable=False)
    scoreline = Column(String(10))  # E.g., "2-1"
    competition = Column(String(50))  # E.g., "Premier League", "Champions League"

    # Relationships
    home_team = relationship("Team", 
                           foreign_keys=[home_team_id],
                           back_populates="home_matches")
    away_team = relationship("Team", 
                           foreign_keys=[away_team_id],
                           back_populates="away_matches")

    def __repr__(self):
        return f"<Match(home={self.home_team_id} vs away={self.away_team_id}, date='{self.match_date}')>"
