# N17 Dashboard

Advanced dashboard system for tracking Tottenham Hotspur transfers and news with AI analysis.

## System Overview

### Data Sources
- **Reddit Integration** (r/coys)
- **News Monitoring** with AI processing
- **Transfer Timeline Tracking**
- **Player Link Analysis**
- API-Football integration (base player data)

### Current Features
1. **Real-time Monitoring**
   - Reddit post monitoring (2 minute intervals)
   - News article processing with LLM
   - Transfer rumor confidence scoring

2. **Core Functionality**
   - Historical data fetching (last 7-30 days)
   - Automated news classification (Tier 1-4 system)
   - Player transfer timelines
   - Club interest tracking
   - News metadata preservation

3. **API Endpoints**
   - Reddit historical data fetching
   - Player statistics updates
   - Transfer link management
   - News reprocessing endpoints

4. **Data Management**
   - JSON storage with automatic backups
   - Background task processing
   - Error handling and retries
   - Rate limiting protection

### Enhanced File Structure
```
n17-dash/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── reddit_service.py
│   │   │   ├── llm_service.py
│   │   │   └── football_api.py
│   │   ├── routers/
│   │   │   ├── api.py
│   │   │   └── views.py
│   │   ├── background.py
│   │   └── main.py
│   ├── data/
│   │   ├── news/            # Processed news articles
│   │   ├── links/           # Player transfer links
│   │   ├── processed_news.json
│   │   └── players/         # Base player info
│   ├── requirements.txt
│   └── venv/
├── tests/
│   └── test_reddit.py
└── .env
```

## Key Data Structures

### Player Transfer File (`data/links/player_[id].json`)
```json
{
  "player_id": 270510,
  "canonical_name": "Mathys Tel",
  "transfer_status": "developing",
  "timeline": [
    {
      "event_type": "meeting",
      "details": "Tottenham presented project...",
      "confidence": 85,
      "date": "2025-01-30T22:08:15.294701",
      "news_ids": ["r-202501302208-1ie1y6t"]
    }
  ],
  "related_clubs": [
    {"name": "Tottenham", "role": "interested"}
  ],
  "direction": "incoming",
  "last_updated": "2025-01-31T12:41:29.558994"
}
```

### News Article (`data/news/r-[id].json`)
```json
{
  "id": "r-202501311139-1ieirhu",
  "source": "reddit",
  "reddit_id": "1ieirhu",
  "timestamp": "2025-01-31T11:39:17.728629",
  "title": "Tottenham boss Daniel Levy meeting with Mathys Tel...",
  "content": "",
  "url": "https://i.redd.it/n2y4poakwcge1.jpeg",
  "tier": 2,
  "metadata": {
    "flair": "Transfer News: Tier 2",
    "saved_at": "2025-01-31T11:39:17.728637"
  }
}
```

## System Setup

1. **Environment Configuration**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **API Credentials (`.env`)**
```
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
API_FOOTBALL_KEY=your_football_api_key
LLM_API_KEY=your_llm_provider_key
```

3. **Service Management**
```bash
# Start main service
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start background workers
python -m app.background
```

## Development Roadmap

### Phase 1: Core Infrastructure ✓
- [x] Reddit integration
- [x] News processing pipeline
- [x] Transfer timeline tracking
- [x] Confidence scoring system

### Phase 2: Enhanced Features (Current)
- [ ] Twitter/X integration
- [ ] Transfer impact predictions
- [ ] Club negotiation simulations
- [ ] Deal success probability models

### Phase 3: Advanced Analytics
- [ ] Player value estimation
- [ ] Contract analysis
- [ ] Wage structure modeling
- [ ] FFP compliance checks

### Phase 4: Visualization
- [ ] Interactive timeline maps
- [ ] Deal negotiation flows
- [ ] Media sentiment analysis
- [ ] Real-time dashboards

## Monitoring & Maintenance

```bash
# Check service status
journalctl -u n17-dash.service -f

# Reprocess unlinked news
curl -X POST http://localhost:8000/api/news/reprocess-unlinked

# Force historical fetch (7 days)
curl -X POST http://localhost:8000/api/reddit/fetch-historical?days=7
```

## Technical Notes

- **Rate Limits**
  - Reddit API: 60 requests/minute
  - LLM Provider: Check service-specific limits
  - API-Football: 100 calls/day (free tier)

- **Data Retention**
  - News articles: Permanent storage
  - Player links: Updated every 15 minutes
  - Processed IDs: Maintained indefinitely

- **Background Workers**
  - Reddit monitoring: 2 minute intervals
  - News processing: 1 minute intervals
  - Stats updates: Daily at 03:00 UTC
