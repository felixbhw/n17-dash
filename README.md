# N17 Dashboard

A lightweight dashboard system for tracking Tottenham Hotspur squad information using API-Football data.

## System Overview

### Data Sources
- API-Football for squad and player statistics
- Future expansion planned for:
  - Club website RSS feed for official announcements
  - News monitoring (r/coys, Twitter)
  - AI-powered news analysis

### Current Features
1. **Squad Information**
   - Basic player details (name, position, number)
   - Player statistics for current season
   - Player photos and metadata

2. **Data Storage**
   - Simple JSON file structure
   - No database required
   - Easy to backup and version control

### File Structure
```
n17-dash/
├── backend/
│   ├── data/                  # JSON data storage
│   │   ├── players/          # Individual player files
│   │   ├── stats/           # Player statistics
│   │   ├── matches/         # Match information (future)
│   │   └── injuries/        # Injury records (future)
│   ├── football_api.py      # API-Football client
│   ├── initial_sync.py      # Data sync script
│   ├── requirements.txt
│   └── venv/               # Python virtual environment
├── frontend/              # (Coming soon)
│   ├── static/           
│   │   ├── css/
│   │   └── js/
│   └── templates/
└── .env                  # API keys and configuration
```

### Data Structure

#### Player Data (`data/players/[player_id].json`)
```json
{
    "id": 123,
    "name": "Player Name",
    "firstname": "Player",
    "lastname": "Name",
    "age": 25,
    "number": 10,
    "position": "Forward",
    "photo": "https://...",
    "last_updated": "2024-01-30T14:47:35.142956"
}
```

#### Player Statistics (`data/stats/player_[id].json`)
```json
{
    "player": {
        "id": 123,
        "name": "Player Name",
        "nationality": "England",
        "height": "180 cm",
        "weight": "75 kg"
    },
    "statistics": [
        {
            "team": { "id": 47, "name": "Tottenham" },
            "league": { "id": 39, "name": "Premier League" },
            "games": {
                "appearences": 20,
                "lineups": 18,
                "minutes": 1620
            },
            "goals": {
                "total": 10,
                "assists": 5
            }
        }
    ]
}
```

## Setup and Usage

1. **Environment Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configuration**
   - Create `.env` file in root directory
   - Add your API-Football key:
     ```
     API_FOOTBALL_KEY=your_key_here
     ```

3. **Initial Data Sync**
   ```bash
   cd backend
   python initial_sync.py
   ```

## Development Roadmap

### Phase 1: Core Features ✓
- [x] API-Football integration
- [x] JSON data storage
- [x] Basic squad information
- [x] Player statistics

### Phase 2: Frontend (In Progress)
- [ ] Simple web interface
- [ ] Squad list view
- [ ] Player detail pages
- [ ] Statistics visualization

### Phase 3: Enhanced Features
- [ ] Match data integration
- [ ] Injury tracking
- [ ] News monitoring
- [ ] Transfer rumors

### Phase 4: AI Integration
- [ ] News classification
- [ ] Transfer reliability scoring
- [ ] Performance prediction
- [ ] Automated reports

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Technical Notes

### API Rate Limits
- Free tier: Limited requests per day
- Pro tier: Higher limits, current season access

### Data Updates
- Squad data updates daily
- Statistics update after matches
- Manual sync available via `initial_sync.py`

### Future Improvements
1. **Automated Updates**
   - Scheduled data syncs
   - WebSocket updates for live data

2. **Data Validation**
   - JSON schema validation
   - Data consistency checks

3. **Frontend Features**
   - Interactive statistics
   - Player comparison tools
   - Performance trends

4. **Data Analysis**
   - Performance metrics
   - Team statistics
   - Historical comparisons
