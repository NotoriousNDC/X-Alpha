PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  handle TEXT NOT NULL,
  display_name TEXT,
  category TEXT,
  notes TEXT,
  UNIQUE(platform, handle)
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  platform_post_id TEXT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  posted_at TEXT NOT NULL,
  text TEXT NOT NULL,
  url TEXT,
  raw JSON
);
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  asset_class TEXT NOT NULL,
  instrument TEXT,
  market_ref TEXT,
  side TEXT NOT NULL,
  team TEXT,
  line_type TEXT,
  line REAL,
  odds_price REAL,
  size REAL,
  confidence REAL,
  horizon_seconds INTEGER,
  expiry_time TEXT,
  extracted JSON,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_signals_account ON signals(account_id);
CREATE INDEX IF NOT EXISTS idx_signals_asset ON signals(asset_class, instrument);
CREATE INDEX IF NOT EXISTS idx_signals_marketref ON signals(market_ref);

CREATE TABLE IF NOT EXISTS price_bars (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL,
  ts TEXT NOT NULL,
  price REAL NOT NULL,
  source TEXT
);
CREATE INDEX IF NOT EXISTS idx_price_bars_inst_ts ON price_bars(instrument, ts);

CREATE TABLE IF NOT EXISTS prediction_quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  market_ref TEXT NOT NULL,
  ts TEXT NOT NULL,
  yes_price REAL,
  no_price REAL
);
CREATE INDEX IF NOT EXISTS idx_prediction_quotes_market_ts ON prediction_quotes(market_ref, ts);

CREATE TABLE IF NOT EXISTS prediction_resolutions (
  market_ref TEXT PRIMARY KEY,
  resolved_at TEXT NOT NULL,
  outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sports_events (
  event_id TEXT PRIMARY KEY,
  league TEXT,
  start_time TEXT,
  team1 TEXT,
  team2 TEXT,
  score1 INTEGER,
  score2 INTEGER
);
CREATE TABLE IF NOT EXISTS sports_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES sports_events(event_id) ON DELETE CASCADE,
  ts TEXT NOT NULL,
  line_type TEXT NOT NULL,
  team TEXT,
  line REAL,
  odds_price REAL,
  is_closing INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sports_lines_event ON sports_lines(event_id, line_type, ts);

CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
  evaluation_window TEXT,
  settled_at TEXT NOT NULL,
  realized_return REAL,
  benchmark_return REAL,
  excess_return REAL,
  sharpe_like REAL,
  brier REAL,
  pnl_per_contract REAL,
  clv_points REAL,
  clv_prob_delta REAL,
  won INTEGER,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS leaderboard (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  window_days INTEGER NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  n_signals INTEGER NOT NULL,
  win_rate REAL,
  mean_excess_return REAL,
  sharpe_like REAL,
  mean_brier REAL,
  mean_clv_points REAL,
  mean_pred_pnl REAL,
  alpha_score REAL,
  details JSON,
  computed_at TEXT DEFAULT (datetime('now'))
);
