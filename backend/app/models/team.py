"""Team model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from . import Base

class Team(Base):
    """Team model representing football teams in the system."""
    
    __tablename__ = 'teams'

    team_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(3))  # E.g., "TOT" for Tottenham
    stadium = Column(String(100))
    manager = Column(String(100))
    league = Column(String(50))
    founded = Column(Integer)  # Founded year

    # Relationships
    players = relationship("Player", back_populates="team")
    home_matches = relationship("Match", 
                              foreign_keys="Match.home_team_id",
                              back_populates="home_team")
    away_matches = relationship("Match", 
                              foreign_keys="Match.away_team_id",
                              back_populates="away_team")

    def __repr__(self):
        return f"<Team(name='{self.name}', code='{self.code}', league='{self.league}')>"
