"""SQLAlchemy models for N17 Dashboard."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Import all models to make them available when importing from models
from .player import Player
from .team import Team
from .injury import Injury
from .transfer import TransferStatus
from .match import Match
from .news import NewsUpdate

__all__ = ['Base', 'Player', 'Team', 'Injury', 'TransferStatus', 'Match', 'NewsUpdate']
