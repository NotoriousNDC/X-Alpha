from __future__ import annotations
import json, pandas as pd
from pathlib import Path
import sys
BASE = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE))
from src.db import get_conn, init_schema
from src.ingest.x_ingest import load_posts_from_csv
from src.parsers import parse_equity, parse_crypto, parse_prediction, parse_sports
from src.scoring.metrics import compute_equity_crypto_outcomes, compute_prediction_outcomes, compute_sports_outcomes, build_leaderboard

def upsert_accounts(conn, df_posts: pd.DataFrame):
    acc = df_posts[['platform','handle']].drop_duplicates().copy()
    acc['display_name'] = acc['handle']
    acc['category'] = df_posts.groupby('handle')['category'].first().reindex(acc['handle']).values
    cur = conn.cursor()
    for _, r in acc.iterrows():
        cur.execute("INSERT OR IGNORE INTO accounts(platform,handle,display_name,category) VALUES (?,?,?,?)",
                    (r['platform'], r['handle'], r['display_name'], r['category']))
    conn.commit()
    rows = conn.execute("SELECT id,platform,handle FROM accounts").fetchall()
    return {(row['platform'], row['handle']): row['id'] for row in rows}

def insert_posts(conn, df_posts: pd.DataFrame, account_map: dict):
    cur = conn.cursor()
    for _, r in df_posts.iterrows():
        posted_at_str = r['posted_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r['posted_at'], 'strftime') else str(r['posted_at'])
        cur.execute("INSERT INTO posts(platform, platform_post_id, account_id, posted_at, text, url, raw) VALUES (?,?,?,?,?,?,?)",
                    (r['platform'], str(r['post_id']), account_map[(r['platform'], r['handle'])], posted_at_str, r['text'], r.get('url',''), json.dumps({})))
    conn.commit()
    return pd.read_sql_query("SELECT * FROM posts", conn)

def parse_and_insert_signals(conn, posts: pd.DataFrame):
    cur = conn.cursor()
    for _, p in posts.iterrows():
        text = p['text']
        all_sigs = []
        for fn in (parse_equity, parse_crypto, parse_prediction, parse_sports):
            try: all_sigs.extend(fn(text))
            except: pass
        for s in all_sigs:
            row = s.to_row()
            # For sports, use instrument as market_ref if market_ref is not set
            if row['asset_class'] == 'sports' and not row.get('market_ref'):
                row['market_ref'] = row.get('instrument')
            cur.execute("""INSERT INTO signals(post_id, account_id, asset_class, instrument, market_ref, side, team, line_type, line, odds_price, size, confidence, horizon_seconds, expiry_time, extracted)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                int(p['id']), int(p['account_id']), row['asset_class'], row.get('instrument'), row.get('market_ref'), row['side'],
                row.get('team'), row.get('line_type'), row.get('line'), row.get('odds_price'), row.get('size'), row.get('confidence'),
                row.get('horizon_seconds'), row.get('expiry_time'), json.dumps(row.get('extracted', {}))
            ))
    conn.commit()
    return pd.read_sql_query("SELECT s.*, p.posted_at, a.handle FROM signals s JOIN posts p ON p.id=s.post_id JOIN accounts a ON a.id=s.account_id", conn)

def load_market_data():
    prices = pd.read_csv(BASE/'examples'/'sample_prices.csv')
    quotes = pd.read_csv(BASE/'examples'/'sample_prediction_quotes.csv')
    resolutions = pd.read_csv(BASE/'examples'/'sample_prediction_resolutions.csv')
    events = pd.read_csv(BASE/'examples'/'sample_sports_events.csv')
    lines = pd.read_csv(BASE/'examples'/'sample_sports_lines.csv')
    return prices, quotes, resolutions, events, lines

def insert_market_data(conn, prices, quotes, resolutions, events, lines):
    prices.to_sql('price_bars', conn, if_exists='replace', index=False)
    quotes.to_sql('prediction_quotes', conn, if_exists='replace', index=False)
    resolutions.to_sql('prediction_resolutions', conn, if_exists='replace', index=False)
    events.to_sql('sports_events', conn, if_exists='replace', index=False)
    lines.to_sql('sports_lines', conn, if_exists='replace', index=False)

def compute_all_outcomes(conn, signals, prices, quotes, resolutions, events, lines):
    # Benchmarks: equities->SPY; crypto->BTC-USD (alts only)
    benchmarks = {}
    for inst in signals['instrument'].dropna().unique():
        if '-' in inst:
            benchmarks[inst] = 'BTC-USD' if inst != 'BTC-USD' else None
        else:
            benchmarks[inst] = 'SPY'
    from src.scoring.metrics import compute_equity_crypto_outcomes, compute_prediction_outcomes, compute_sports_outcomes
    eqcr = compute_equity_crypto_outcomes(signals[signals['asset_class'].isin(['equity','crypto'])], prices, benchmarks)
    pm = compute_prediction_outcomes(signals[signals['asset_class']=='prediction'], quotes, resolutions)
    sp = compute_sports_outcomes(signals[signals['asset_class']=='sports'], events, lines)
    outcomes = pd.concat([df for df in [eqcr, pm, sp] if not df.empty], ignore_index=True)
    outcomes.to_sql('outcomes', conn, if_exists='replace', index=False)
    return outcomes

def compute_and_store_leaderboard(conn, signals, outcomes):
    lb = build_leaderboard(pd.read_sql_query("SELECT * FROM accounts", conn), signals, outcomes, window_days=90)
    lb.to_sql('leaderboard', conn, if_exists='replace', index=False)
    lb.to_csv(BASE/'leaderboard.csv', index=False)
    return lb

def main():
    db_path = BASE/'alpha_tracker.db'
    conn = get_conn(db_path)
    init_schema(conn, BASE/'schema'/'schema.sql')
    posts_df = load_posts_from_csv(BASE/'examples'/'sample_posts.csv')
    account_map = upsert_accounts(conn, posts_df)
    posts = insert_posts(conn, posts_df, account_map)
    signals = parse_and_insert_signals(conn, posts)
    prices, quotes, resolutions, events, lines = load_market_data()
    insert_market_data(conn, prices, quotes, resolutions, events, lines)
    outcomes = compute_all_outcomes(conn, signals, prices, quotes, resolutions, events, lines)
    lb = compute_and_store_leaderboard(conn, signals, outcomes)
    print("Demo complete!")
    print("\nTop Alpha Accounts:")
    print(lb[['account_id','alpha_score','n_signals','win_rate','mean_excess_return']].head())

if __name__ == "__main__":
    main()
