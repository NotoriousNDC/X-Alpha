"""Setup and configuration script for Alpha Tracker."""
import os
import sys
from pathlib import Path
import sqlite3
import json

BASE = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE))

from src.db import get_conn, init_schema

def setup_directories():
    """Create necessary directories."""
    dirs = ['logs', 'exports', 'backups', 'data']
    for dir_name in dirs:
        dir_path = BASE / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"[OK] Created {dir_name}/ directory")

def setup_database():
    """Initialize database with schema."""
    db_path = BASE / 'alpha_tracker.db'
    schema_path = BASE / 'schema' / 'schema.sql'
    
    if db_path.exists():
        response = input("Database already exists. Reinitialize? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing database")
            return
        
        # Backup existing database
        backup_path = BASE / 'backups' / f'alpha_tracker_backup_{Path(db_path).stat().st_mtime:.0f}.db'
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Backed up existing database to {backup_path}")
    
    conn = get_conn(db_path)
    init_schema(conn, schema_path)
    print("[OK] Database initialized")

def setup_config():
    """Create configuration file."""
    config_path = BASE / 'config.json'
    
    if config_path.exists():
        print("Config file already exists")
        return
    
    config = {
        "x_api": {
            "bearer_token": "",
            "api_key": "",
            "api_secret": ""
        },
        "market_data": {
            "yahoo_finance": True,
            "alpha_vantage_key": "",
            "coingecko_api_key": "",
            "polygon_api_key": ""
        },
        "prediction_markets": {
            "polymarket_enabled": True,
            "manifold_enabled": True,
            "metaculus_enabled": False
        },
        "sports": {
            "odds_api_key": "",
            "leagues": ["NFL", "NBA", "MLB", "NHL"]
        },
        "scheduler": {
            "fetch_interval_hours": 1,
            "compute_interval_hours": 6,
            "leaderboard_interval_hours": 12,
            "backup_interval_days": 1
        },
        "filters": {
            "min_quality_score": 0.3,
            "min_confidence": 0.0,
            "max_age_days": 90
        },
        "tracking": {
            "handles": [
                "fintwit_alpha",
                "crypto_whale",
                "sports_sharp",
                "prediction_pro"
            ]
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("[OK] Created config.json template")
    print("  Edit config.json to add API keys and customize settings")

def setup_environment():
    """Create .env file template."""
    env_path = BASE / '.env'
    
    if env_path.exists():
        print(".env file already exists")
        return
    
    env_content = """# Alpha Tracker Environment Variables

# X (Twitter) API
X_BEARER_TOKEN=

# Market Data APIs
ALPHA_VANTAGE_KEY=
COINGECKO_API_KEY=
POLYGON_API_KEY=

# Sports Data
ODDS_API_KEY=

# Database
DB_PATH=alpha_tracker.db

# Scheduler
FETCH_HOURS=24
MIN_QUALITY=0.3

# Dashboard
STREAMLIT_PORT=8501
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print("[OK] Created .env template")
    print("  Add your API keys to .env file")

def load_sample_accounts():
    """Load sample accounts to track."""
    sample_accounts = [
        ("x", "fintwit_alpha", "FinTwit Alpha", "equity"),
        ("x", "crypto_whale", "Crypto Whale", "crypto"),
        ("x", "sports_sharp", "Sports Sharp", "sports"),
        ("x", "prediction_pro", "Prediction Pro", "prediction"),
        ("x", "options_flow", "Options Flow", "equity"),
        ("x", "btc_maximalist", "BTC Maximalist", "crypto"),
        ("x", "nba_analytics", "NBA Analytics", "sports"),
        ("x", "macro_trader", "Macro Trader", "equity"),
        ("x", "defi_farmer", "DeFi Farmer", "crypto"),
        ("x", "election_trader", "Election Trader", "prediction")
    ]
    
    db_path = BASE / 'alpha_tracker.db'
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    for platform, handle, display_name, category in sample_accounts:
        cur.execute("""
            INSERT OR IGNORE INTO accounts (platform, handle, display_name, category)
            VALUES (?, ?, ?, ?)
        """, (platform, handle, display_name, category))
    
    conn.commit()
    print(f"[OK] Loaded {len(sample_accounts)} sample accounts")

def check_dependencies():
    """Check if required packages are installed."""
    required = [
        'pandas', 'numpy', 'streamlit', 'plotly', 
        'requests', 'schedule', 'python-dateutil'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"[WARNING] Missing packages: {', '.join(missing)}")
        print(f"  Run: pip install {' '.join(missing)}")
        return False
    
    print("[OK] All dependencies installed")
    return True

def print_quickstart():
    """Print quickstart instructions."""
    print("\n" + "="*50)
    print("Alpha Tracker Setup Complete!")
    print("="*50)
    print("\nQuick Start Guide:")
    print("\n1. Configure API keys:")
    print("   - Edit .env file with your API credentials")
    print("   - Or set environment variables directly")
    
    print("\n2. Run demo pipeline:")
    print("   python examples/demo_pipeline.py")
    
    print("\n3. Start dashboard:")
    print("   streamlit run dashboard.py")
    
    print("\n4. Schedule automated updates:")
    print("   python scripts/scheduler.py")
    
    print("\n5. Export data:")
    print("   python scripts/export_utils.py --type leaderboard --format csv")
    
    print("\n" + "="*50)
    print("Documentation: See README.md for full details")
    print("="*50)

def main():
    """Run complete setup."""
    print("\n>>> Alpha Tracker Setup")
    print("="*50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("[WARNING] Python 3.8+ required")
        return
    
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        return
    
    print("\n2. Creating directories...")
    setup_directories()
    
    print("\n3. Setting up database...")
    setup_database()
    
    print("\n4. Creating config files...")
    setup_config()
    setup_environment()
    
    print("\n5. Loading sample accounts...")
    load_sample_accounts()
    
    print_quickstart()

if __name__ == "__main__":
    main()
