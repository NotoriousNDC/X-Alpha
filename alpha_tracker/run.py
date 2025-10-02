#!/usr/bin/env python
"""Main entry point for Alpha Tracker."""
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Alpha Tracker - Track and score alpha-leaking accounts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py setup              # Initial setup
  python run.py demo               # Run demo pipeline
  python run.py dashboard          # Launch dashboard
  python run.py scheduler          # Start scheduler
  python run.py export leaderboard # Export leaderboard
  python run.py fetch              # Fetch new posts
        """
    )
    
    parser.add_argument('command', 
                       choices=['setup', 'demo', 'dashboard', 'scheduler', 
                               'export', 'fetch', 'analyze'],
                       help='Command to run')
    
    parser.add_argument('--type', help='Export type (for export command)')
    parser.add_argument('--format', default='csv', help='Export format')
    parser.add_argument('--account', help='Account handle')
    parser.add_argument('--days', type=int, default=30, help='Days to look back')
    
    args = parser.parse_args()
    
    BASE = Path(__file__).resolve().parent
    
    if args.command == 'setup':
        # Run setup
        sys.path.append(str(BASE))
        from scripts.setup import main as setup_main
        setup_main()
    
    elif args.command == 'demo':
        # Run demo pipeline
        sys.path.append(str(BASE))
        from examples.demo_pipeline import main as demo_main
        demo_main()
    
    elif args.command == 'dashboard':
        # Launch Streamlit dashboard
        import subprocess
        subprocess.run(['streamlit', 'run', str(BASE / 'dashboard.py')])
    
    elif args.command == 'scheduler':
        # Start scheduler
        sys.path.append(str(BASE))
        from scripts.scheduler import main as scheduler_main
        scheduler_main()
    
    elif args.command == 'export':
        # Export data
        sys.path.append(str(BASE))
        from scripts.export_utils import DataExporter
        
        db_path = BASE / 'alpha_tracker.db'
        exporter = DataExporter(db_path)
        
        if args.type == 'leaderboard':
            path = exporter.export_leaderboard(format=args.format)
        elif args.type == 'signals':
            path = exporter.export_signals(
                account_handle=args.account,
                days_back=args.days,
                format=args.format
            )
        elif args.type == 'report' and args.account:
            path = exporter.export_performance_report(
                args.account,
                format=args.format or 'html'
            )
        else:
            print("Specify --type (leaderboard, signals, or report)")
            return
        
        print(f"Exported to: {path}")
    
    elif args.command == 'fetch':
        # Fetch new posts
        sys.path.append(str(BASE))
        from src.ingest.x_ingest import generate_sample_posts
        
        print("Fetching new posts...")
        posts = generate_sample_posts(10)
        print(f"Fetched {len(posts)} posts")
        # In production, this would use the real X API
    
    elif args.command == 'analyze':
        # Quick analysis
        import pandas as pd
        sys.path.append(str(BASE))
        from src.db import get_conn
        
        conn = get_conn(BASE / 'alpha_tracker.db')
        
        # Get summary stats
        stats = {
            'accounts': conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0],
            'posts': conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
            'signals': conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
            'outcomes': conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
        }
        
        print("\n=== Alpha Tracker Statistics ===")
        print("="*40)
        for key, value in stats.items():
            print(f"{key.capitalize():12} {value:,}")
        
        # Top performers
        print("\n=== Top Alpha Accounts ===")
        print("="*40)
        
        query = """
        SELECT a.handle, l.alpha_score, l.n_signals
        FROM leaderboard l
        JOIN accounts a ON l.account_id = a.id
        WHERE l.window_days = 90
        ORDER BY l.alpha_score DESC
        LIMIT 5
        """
        
        top = pd.read_sql_query(query, conn)
        if not top.empty:
            for _, row in top.iterrows():
                print(f"@{row['handle']:20} Score: {row['alpha_score']:.3f} ({row['n_signals']} signals)")
        else:
            print("No leaderboard data yet")

if __name__ == "__main__":
    main()
