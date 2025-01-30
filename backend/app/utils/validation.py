"""
Validation utilities for N17 Dashboard.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

class APIResponse(BaseModel):
    """Base model for API-Football responses."""
    get: Optional[str]
    parameters: Optional[Dict[str, Any]]
    errors: Union[List[str], Dict[str, str], Dict[str, Any]] = []
    results: Optional[int]
    response: Union[List[Dict[str, Any]], Dict[str, Any]]

    @validator('response')
    def validate_response_not_empty(cls, v):
        """Ensure response is not empty."""
        if isinstance(v, list) and not v:
            raise ValueError("API response is empty")
        return v

class PlayerValidation(BaseModel):
    """Validation model for player data."""
    player_id: int
    name: str
    date_of_birth: Optional[datetime]
    nationality: Optional[str]
    position: str
    team_id: int

    @validator('position')
    def validate_position(cls, v):
        """Normalize player position."""
        valid_positions = {
            'G': 'Goalkeeper',
            'D': 'Defender',
            'M': 'Midfielder',
            'F': 'Forward',
            'Goalkeeper': 'Goalkeeper',
            'Defender': 'Defender',
            'Midfielder': 'Midfielder',
            'Forward': 'Forward',
            'Attacker': 'Forward'
        }
        normalized = valid_positions.get(v)
        if not normalized:
            raise ValueError(f"Invalid position: {v}")
        return normalized

class InjuryValidation(BaseModel):
    """Validation model for injury data."""
    player_id: int
    description: Optional[str]
    injury_date: datetime
    recovery_estimated: Optional[datetime] = Field(alias='expected_return')
    severity: Optional[str]

    @validator('severity')
    def validate_severity(cls, v):
        """Map injury type to severity."""
        if not v:
            return None
            
        severity_map = {
            'Knock': 'Minor',
            'Muscle Injury': 'Moderate',
            'ACL': 'Severe',
            'MCL': 'Severe',
            'Ankle Injury': 'Moderate',
            'Unknown': None
        }
        return severity_map.get(v, v)

class MatchValidation(BaseModel):
    """Validation model for match data."""
    match_id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime
    scoreline: Optional[str]
    competition: str

    @validator('competition')
    def validate_competition(cls, v):
        """Normalize competition names."""
        competition_map = {
            'Premier League': 'Premier League',
            'FA Cup': 'FA Cup',
            'EFL Cup': 'League Cup',
            'UEFA Champions League': 'Champions League',
            'UEFA Europa League': 'Europa League',
            'UEFA Europa Conference League': 'Conference League'
        }
        return competition_map.get(v, v)

class TransferValidation(BaseModel):
    """Validation model for transfer data."""
    player_id: int
    status: str
    last_update: datetime
    destination_club: Optional[str]
    transfer_fee: Optional[float]

    @validator('status')
    def validate_status(cls, v):
        """Map API transfer status to system status."""
        status_map = {
            'Confirmed': 'Completed',
            'Done Deal': 'Completed',
            'Rumour': 'Rumored',
            'Talks': 'In Progress'
        }
        return status_map.get(v, v)

    @validator('transfer_fee')
    def validate_transfer_fee(cls, v):
        """Convert transfer fee to millions and handle currency."""
        if not v:
            return None
        # Assume fee is in euros, convert to millions
        return round(float(v) / 1_000_000, 2)

def validate_api_response(response: dict) -> dict:
    """Validate the structure of API-Football responses."""
    if not isinstance(response, dict):
        raise ValueError("API response must be a dictionary")
    
    if response.get("errors"):
        logger.error(f"API errors: {response['errors']}")
        return {}
        
    if "response" not in response:
        logger.error("Invalid API response structure")
        return {}
    
    return response["response"]  # Return the actual data payload

def validate_player_data(player_data: Dict) -> Optional[Dict]:
    """Validate and normalize player data."""
    try:
        validated = PlayerValidation(**player_data)
        return validated.dict()
    except Exception as e:
        logger.error(f"Player data validation failed: {str(e)}")
        return None

def validate_injury_data(injury_data: Dict) -> Optional[Dict]:
    """Validate and normalize injury data."""
    try:
        validated = InjuryValidation(**injury_data)
        return validated.dict()
    except Exception as e:
        logger.error(f"Injury data validation failed: {str(e)}")
        return None

def validate_match_data(match_data: Dict) -> Optional[Dict]:
    """Validate and normalize match data."""
    try:
        validated = MatchValidation(**match_data)
        return validated.dict()
    except Exception as e:
        logger.error(f"Match data validation failed: {str(e)}")
        return None

def validate_transfer_data(transfer_data: Dict) -> Optional[Dict]:
    """Validate and normalize transfer data."""
    try:
        validated = TransferValidation(**transfer_data)
        return validated.dict()
    except Exception as e:
        logger.error(f"Transfer data validation failed: {str(e)}")
        return None
