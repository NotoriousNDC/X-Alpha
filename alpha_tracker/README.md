# Alpha Tracker - X Account Signal Analysis System

A comprehensive system for discovering, tracking, and scoring "alpha-leaking" accounts on X (Twitter) across multiple domains: equities, crypto, prediction markets, and sports betting.

## Features

- **Multi-Domain Signal Parsing**: Extracts tradable signals from text across 4 asset classes
- **Automated Outcome Tracking**: Matches signals against market data to compute realized performance
- **Alpha Scoring**: Composite scoring system using multiple metrics (returns, Sharpe, CLV, Brier scores)
- **Account Discovery**: Tools to find new high-signal accounts based on engagement and content patterns
- **Rolling Leaderboards**: Track account performance over configurable time windows

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database and run demo
python examples/demo_pipeline.py

# 3. View results
cat leaderboard.csv
```

## System Architecture

### Data Flow
```
X Posts → Parser → Signals → Market Data → Outcomes → Leaderboard
```

### Database Schema

**Core Tables:**
- `accounts`: X account profiles and metadata
- `posts`: Raw posts/tweets with timestamps
- `signals`: Parsed trading/betting signals
- `outcomes`: Realized performance metrics
- `leaderboard`: Aggregated account scores

**Market Data Tables:**
- `price_bars`: Equity/crypto price snapshots
- `prediction_quotes`: Prediction market prices
- `prediction_resolutions`: Market outcomes
- `sports_events`: Game results
- `sports_lines`: Betting lines and odds

## Signal Parsing

### Equities
- Detects: $TICKERS, buy/sell signals, price targets, stop losses
- Extracts: Confidence levels, position sizes, time horizons
- Example: "$AAPL PT $195, SL $188" → long signal with targets

### Crypto
- Detects: Token symbols, leverage, perp/spot trades
- Extracts: Multiple TPs, entry/exit levels, position sizes
- Example: "$SOL 3x leverage, TP1 $115" → leveraged long

### Prediction Markets
- Detects: Platform links (Polymarket, Manifold, etc.)
- Extracts: YES/NO positions, probabilities, bet sizes
- Example: "Polymarket Fed cuts 35%, buying YES" → YES position

### Sports Betting
- Detects: Spreads, totals, moneylines across major leagues
- Extracts: Unit sizes, CLV opportunities, confidence
- Example: "Chiefs -3.5, 5 units" → spread bet with size

## Scoring Methodology

### Alpha Score Components

1. **Win Rate**: Percentage of profitable signals
2. **Excess Return**: Return above benchmark (SPY for stocks, BTC for alts)
3. **Sharpe-like Ratio**: Risk-adjusted returns
4. **Brier Score**: Calibration for probability predictions
5. **CLV (Closing Line Value)**: For sports - beating the closing line
6. **PnL per Contract**: Prediction market profitability

### Composite Score
```python
alpha_score = mean(z_scores_of_components)
```

## Usage Examples

### Ingest Posts from CSV
```python
from src.ingest.x_ingest import load_posts_from_csv
posts = load_posts_from_csv('data/posts.csv')
```

### Parse Signals
```python
from src.parsers import parse_equity, parse_crypto
signals = parse_equity("$AAPL buy at $190, target $195")
```

### Compute Outcomes
```python
from src.scoring.metrics import compute_equity_crypto_outcomes
outcomes = compute_equity_crypto_outcomes(signals, prices, benchmarks)
```

### Generate Leaderboard
```python
from src.scoring.metrics import build_leaderboard
leaderboard = build_leaderboard(accounts, signals, outcomes, window_days=90)
```

## API Integration

### X API Setup
```python
from src.ingest.x_ingest import XAPIClient

client = XAPIClient(bearer_token='YOUR_TOKEN')
tweets = client.get_user_tweets(user_id, max_results=100)
```

### Account Discovery
```python
from src.ingest.x_ingest import discover_alpha_accounts

search_terms = ['$AAPL target', 'polymarket', 'NFL spread']
accounts = discover_alpha_accounts(bearer_token, search_terms)
```

## Configuration

### Environment Variables
```bash
X_BEARER_TOKEN=your_twitter_api_token
DB_PATH=alpha_tracker.db
```

### Parser Thresholds
Edit parsers to adjust confidence thresholds, pattern matching, etc.

## Data Requirements

### Posts CSV Format
```csv
platform,handle,posted_at,text
x,fintwit_alpha,2024-01-15 09:30:00,"$AAPL breakout..."
```

### Price Data Format
```csv
instrument,ts,price,source
AAPL,2024-01-15 16:00:00,191.25,yahoo
```

## Production Deployment

### Database Migration
```sql
-- Convert to PostgreSQL
-- Schema in schema/schema.sql is portable
```

### Scheduling
```python
# Run every hour
import schedule
schedule.every().hour.do(run_pipeline)
```

### Monitoring
- Track API rate limits
- Monitor parser success rates
- Alert on database growth

## Extending the System

### Add New Asset Class
1. Create parser in `src/parsers/new_asset.py`
2. Add market data tables to schema
3. Implement outcome calculation in `src/scoring/metrics.py`
4. Update leaderboard aggregation

### Add New Metrics
1. Compute in outcome calculation
2. Add to leaderboard aggregation
3. Include in alpha score if relevant

## Testing

```bash
# Run tests
pytest tests/

# Test parser
python -c "from src.parsers import parse_equity; print(parse_equity('$AAPL buy 190'))"
```

## Limitations

- Requires explicit, parseable signals (no vague commentary)
- Alpha decay not modeled (crowding effects)
- No slippage/execution modeling
- Simple benchmarking (could add factor models)

## License

MIT

## Support

For issues or questions, please open a GitHub issue or contact the maintainers.