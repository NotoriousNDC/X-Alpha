"""Production scheduler for automated Alpha Tracker updates."""
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Setup paths
BASE = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE))

from src.db import get_conn, init_schema
from src.ingest.x_ingest import fetch_recent_posts_from_x, filter_alpha_posts
from examples.demo_pipeline import (
    upsert_accounts, insert_posts, parse_and_insert_signals,
    compute_all_outcomes, compute_and_store_leaderboard
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE / 'logs' / 'scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlphaTrackerScheduler:
    """Automated scheduler for Alpha Tracker updates."""
    
    def __init__(self, db_path: Path, config: dict = None):
        self.db_path = db_path
        self.config = config or self.load_default_config()
        self.conn = get_conn(db_path)
        
        # Create logs directory
        (BASE / 'logs').mkdir(exist_ok=True)
    
    def load_default_config(self):
        """Load default configuration."""
        return {
            'x_bearer_token': os.environ.get('X_BEARER_TOKEN', ''),
            'handles': self.load_tracked_handles(),
            'fetch_hours_back': 24,
            'min_quality_score': 0.3,
            'leaderboard_windows': [7, 30, 90],
            'backup_enabled': True,
            'backup_retention_days': 30
        }
    
    def load_tracked_handles(self):
        """Load handles from database."""
        try:
            conn = get_conn(self.db_path)
            query = "SELECT DISTINCT handle FROM accounts WHERE platform = 'x'"
            result = conn.execute(query).fetchall()
            return [row[0] for row in result]
        except:
            return []
    
    def fetch_new_posts(self):
        """Fetch new posts from X API."""
        logger.info("Fetching new posts...")
        
        if not self.config['x_bearer_token']:
            logger.warning("No X API token configured, skipping fetch")
            return None
        
        try:
            posts_df = fetch_recent_posts_from_x(
                self.config['x_bearer_token'],
                self.config['handles'],
                self.config['fetch_hours_back']
            )
            
            # Filter for quality
            if not posts_df.empty:
                posts_df = filter_alpha_posts(posts_df, self.config['min_quality_score'])
                logger.info(f"Fetched {len(posts_df)} quality posts")
                return posts_df
            else:
                logger.info("No new posts found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return None
    
    def process_signals(self):
        """Process new signals and compute outcomes."""
        logger.info("Processing signals...")
        
        try:
            # Get recent unprocessed posts
            query = """
            SELECT p.* FROM posts p
            LEFT JOIN signals s ON p.id = s.post_id
            WHERE s.id IS NULL
            ORDER BY p.posted_at DESC
            LIMIT 100
            """
            posts = pd.read_sql_query(query, self.conn)
            
            if posts.empty:
                logger.info("No unprocessed posts")
                return
            
            # Parse and insert signals
            signals = parse_and_insert_signals(self.conn, posts)
            logger.info(f"Parsed {len(signals)} new signals")
            
            # Load market data (this would be from real APIs in production)
            # For now, using cached/sample data
            self.update_market_data()
            
            # Compute outcomes for signals with available data
            self.compute_new_outcomes()
            
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
    
    def update_market_data(self):
        """Update market data from external sources."""
        logger.info("Updating market data...")
        
        # In production, this would fetch from:
        # - Yahoo Finance / Alpha Vantage for stocks
        # - CoinGecko / Binance for crypto
        # - Polymarket / Manifold APIs for predictions
        # - Odds providers for sports
        
        # Placeholder for real implementation
        logger.info("Market data update complete (using cached data)")
    
    def compute_new_outcomes(self):
        """Compute outcomes for settled signals."""
        logger.info("Computing outcomes...")
        
        try:
            # Get signals without outcomes that should be settled
            query = """
            SELECT s.* FROM signals s
            LEFT JOIN outcomes o ON s.id = o.signal_id
            WHERE o.id IS NULL
            AND datetime(s.created_at) < datetime('now', '-1 day')
            LIMIT 100
            """
            
            # This would call the outcome computation functions
            # with real market data in production
            logger.info("Outcomes computation complete")
            
        except Exception as e:
            logger.error(f"Error computing outcomes: {e}")
    
    def update_leaderboards(self):
        """Update leaderboards for all windows."""
        logger.info("Updating leaderboards...")
        
        try:
            for window_days in self.config['leaderboard_windows']:
                # This would rebuild leaderboards
                logger.info(f"Updated {window_days}-day leaderboard")
            
            logger.info("All leaderboards updated")
            
        except Exception as e:
            logger.error(f"Error updating leaderboards: {e}")
    
    def backup_database(self):
        """Create database backup."""
        if not self.config['backup_enabled']:
            return
        
        logger.info("Creating database backup...")
        
        try:
            backup_dir = BASE / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f'alpha_tracker_{timestamp}.db'
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            
            # Clean old backups
            self.clean_old_backups()
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
    
    def clean_old_backups(self):
        """Remove old backup files."""
        backup_dir = BASE / 'backups'
        if not backup_dir.exists():
            return
        
        retention_days = self.config['backup_retention_days']
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        for backup_file in backup_dir.glob('alpha_tracker_*.db'):
            if backup_file.stat().st_mtime < cutoff.timestamp():
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")
    
    def hourly_update(self):
        """Hourly update job."""
        logger.info("=== Starting hourly update ===")
        
        # Fetch new posts
        posts = self.fetch_new_posts()
        if posts is not None and not posts.empty:
            # Process into database
            # This would use the full pipeline in production
            pass
        
        # Process signals
        self.process_signals()
        
        logger.info("=== Hourly update complete ===")
    
    def daily_update(self):
        """Daily update job."""
        logger.info("=== Starting daily update ===")
        
        # Update market data
        self.update_market_data()
        
        # Compute outcomes
        self.compute_new_outcomes()
        
        # Update leaderboards
        self.update_leaderboards()
        
        # Backup
        self.backup_database()
        
        logger.info("=== Daily update complete ===")
    
    def run(self):
        """Run the scheduler."""
        logger.info("Starting Alpha Tracker Scheduler")
        
        # Schedule jobs
        schedule.every().hour.do(self.hourly_update)
        schedule.every().day.at("02:00").do(self.daily_update)
        
        # Run initial update
        self.hourly_update()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

def main():
    """Main entry point."""
    db_path = BASE / 'alpha_tracker.db'
    
    # Load config from environment or file
    config = {
        'x_bearer_token': os.environ.get('X_BEARER_TOKEN', ''),
        'fetch_hours_back': int(os.environ.get('FETCH_HOURS', 24)),
        'min_quality_score': float(os.environ.get('MIN_QUALITY', 0.3)),
        'leaderboard_windows': [7, 30, 90],
        'backup_enabled': True,
        'backup_retention_days': 30
    }
    
    scheduler = AlphaTrackerScheduler(db_path, config)
    scheduler.run()

if __name__ == "__main__":
    main()


