# Alpha Tracker - Quick Start Guide

## What's Been Built

You now have a complete **Alpha Tracking System** for analyzing X (Twitter) accounts that share trading/betting signals across:
- **Equities** - Stock picks with targets/stops
- **Crypto** - Token trades with leverage
- **Prediction Markets** - Polymarket/Manifold bets
- **Sports Betting** - Spreads, totals, moneylines

## System Components

### 1. **Signal Parsers** (`src/parsers/`)
- Extract tradable signals from raw text
- Identify tickers, positions, confidence levels
- Parse entry/exit prices, bet sizes

### 2. **Scoring Engine** (`src/scoring/`)
- Compute win rates and excess returns
- Calculate Sharpe ratios and Brier scores
- Track CLV (closing line value) for sports
- Generate composite Alpha Scores

### 3. **Data Pipeline** (`examples/demo_pipeline.py`)
- Ingest posts → Parse signals → Match outcomes → Score accounts

### 4. **Dashboard** (`dashboard.py`)
- Interactive Streamlit visualization
- Leaderboards and performance charts
- Account deep-dives and analytics

### 5. **Production Tools** (`scripts/`)
- Automated scheduler for updates
- Data export in multiple formats
- Backup and restore utilities

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Demo Pipeline
```bash
python examples/demo_pipeline.py
```

### 3. Launch Dashboard
```bash
streamlit run dashboard.py
```
Then open http://localhost:8501

### 4. View Results
```bash
# Show statistics
python run.py analyze

# Export leaderboard
python run.py export --type leaderboard

# Generate account report
python scripts/export_utils.py --type report --account fintwit_alpha --format html
```

## Production Setup

### 1. Configure API Keys
Edit `.env` file:
```
X_BEARER_TOKEN=your_token_here
ALPHA_VANTAGE_KEY=your_key
COINGECKO_API_KEY=your_key
```

### 2. Start Scheduler
```bash
python scripts/scheduler.py
```
This will:
- Fetch new posts every hour
- Update market data daily
- Recompute leaderboards
- Create automatic backups

### 3. Track New Accounts
Add accounts to monitor in `config.json`:
```json
{
  "tracking": {
    "handles": [
      "new_alpha_account",
      "another_trader"
    ]
  }
}
```

## Key Features

### Signal Detection
- **Equities**: `$AAPL PT $195` → Long signal with target
- **Crypto**: `$SOL 3x leverage` → Leveraged position
- **Prediction**: `Polymarket YES 65%` → Prediction bet
- **Sports**: `Chiefs -3.5` → Spread bet

### Performance Metrics
- **Win Rate**: % of profitable signals
- **Excess Return**: Return above benchmark
- **Sharpe Ratio**: Risk-adjusted returns
- **CLV**: Beating closing lines (sports)
- **Brier Score**: Prediction calibration

### Alpha Score Formula
```
alpha_score = mean(z_scores([
    win_rate,
    excess_return,
    sharpe_ratio,
    clv_points,
    -brier_score
]))
```

## Directory Structure
```
alpha_tracker/
├── src/
│   ├── parsers/     # Signal extraction
│   ├── scoring/     # Metrics calculation
│   ├── ingest/      # Data ingestion
│   └── utils/       # Helper functions
├── examples/        # Demo data & pipeline
├── scripts/         # Production utilities
├── exports/         # Data exports
├── logs/           # Application logs
└── backups/        # Database backups
```

## Database Schema
- **accounts**: X account profiles
- **posts**: Raw tweets/posts
- **signals**: Parsed trading signals
- **outcomes**: Realized performance
- **leaderboard**: Aggregated scores
- **price_bars**: Market prices
- **prediction_quotes**: Prediction markets
- **sports_lines**: Betting lines

## Next Steps

1. **Add Real Data Sources**
   - Connect X API for live posts
   - Integrate market data feeds
   - Add prediction market APIs

2. **Customize Parsers**
   - Add domain-specific patterns
   - Tune confidence thresholds
   - Handle new signal types

3. **Enhance Scoring**
   - Add risk metrics
   - Model alpha decay
   - Track slippage

4. **Scale Up**
   - Migrate to PostgreSQL
   - Add Redis caching
   - Deploy to cloud

## Troubleshooting

**No signals parsed?**
- Check parser patterns match your text format
- Lower `min_quality_score` in config

**Missing outcomes?**
- Ensure market data is available
- Check signal timestamps match data

**Dashboard won't load?**
- Install streamlit: `pip install streamlit`
- Check port 8501 is available

## Support

See `README.md` for detailed documentation.

---
*Alpha Tracker v1.0 - Built for discovering and tracking trading signal quality*



