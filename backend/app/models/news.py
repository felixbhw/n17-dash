"""News model for N17 Dashboard."""

from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class NewsUpdate(Base):
    """NewsUpdate model representing news and updates about players/team."""
    
    __tablename__ = 'news_updates'

    news_id = Column(Integer, primary_key=True)
    news_text = Column(String(1000), nullable=False)
    reliability_tier = Column(Integer)  # 1 = High, 2 = Medium, 3 = Low
    update_date = Column(Date, nullable=False)
    category = Column(String(20))  # E.g., Injury/Transfer/Rumors
    player_id = Column(Integer, ForeignKey('players.player_id'))
    source = Column(String(50))  # E.g., BBC/Twitter/Reddit
    confidence_score = Column(Float)  # AI-generated confidence score

    # Relationships
    player = relationship("Player", back_populates="news_updates")

    def __repr__(self):
        return f"<NewsUpdate(category='{self.category}', tier={self.reliability_tier}, date='{self.update_date}')>"
