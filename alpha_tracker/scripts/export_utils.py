"""Data export and reporting utilities for Alpha Tracker."""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE))

from src.db import get_conn

class DataExporter:
    """Export Alpha Tracker data in various formats."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = get_conn(db_path)
        self.export_dir = BASE / 'exports'
        self.export_dir.mkdir(exist_ok=True)
    
    def export_leaderboard(self, window_days: int = 90, format: str = 'csv'):
        """Export leaderboard data."""
        query = """
        SELECT 
            a.handle,
            a.category,
            l.n_signals,
            l.win_rate,
            l.mean_excess_return,
            l.sharpe_like,
            l.mean_brier,
            l.mean_clv_points,
            l.mean_pred_pnl,
            l.alpha_score
        FROM leaderboard l
        JOIN accounts a ON l.account_id = a.id
        WHERE l.window_days = ?
        ORDER BY l.alpha_score DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(window_days,))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"leaderboard_{window_days}d_{timestamp}"
        
        if format == 'csv':
            path = self.export_dir / f"{filename}.csv"
            df.to_csv(path, index=False)
        elif format == 'json':
            path = self.export_dir / f"{filename}.json"
            df.to_json(path, orient='records', indent=2)
        elif format == 'excel':
            path = self.export_dir / f"{filename}.xlsx"
            df.to_excel(path, index=False, sheet_name='Leaderboard')
        
        return path
    
    def export_signals(self, account_handle: str = None, 
                      asset_class: str = None,
                      days_back: int = 30,
                      format: str = 'csv'):
        """Export signals with filters."""
        query = """
        SELECT 
            s.*,
            a.handle,
            p.posted_at,
            p.text,
            o.realized_return,
            o.excess_return,
            o.won,
            o.clv_points,
            o.pnl_per_contract
        FROM signals s
        JOIN accounts a ON s.account_id = a.id
        JOIN posts p ON s.post_id = p.id
        LEFT JOIN outcomes o ON s.id = o.signal_id
        WHERE 1=1
        """
        
        params = []
        
        if account_handle:
            query += " AND a.handle = ?"
            params.append(account_handle)
        
        if asset_class:
            query += " AND s.asset_class = ?"
            params.append(asset_class)
        
        if days_back:
            cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()
            query += " AND p.posted_at > ?"
            params.append(cutoff)
        
        query += " ORDER BY s.id DESC"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Clean up extracted column for export
        if 'extracted' in df.columns:
            df['extracted'] = df['extracted'].apply(lambda x: json.loads(x) if x else {})
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"signals_{timestamp}"
        
        if format == 'csv':
            path = self.export_dir / f"{filename}.csv"
            df.to_csv(path, index=False)
        elif format == 'json':
            path = self.export_dir / f"{filename}.json"
            df.to_json(path, orient='records', indent=2, default_handler=str)
        
        return path
    
    def export_performance_report(self, account_handle: str, format: str = 'html'):
        """Generate comprehensive performance report for an account."""
        # Get account info
        account_query = """
        SELECT * FROM accounts WHERE handle = ?
        """
        account = pd.read_sql_query(account_query, self.conn, params=(account_handle,))
        
        if account.empty:
            raise ValueError(f"Account {account_handle} not found")
        
        account_id = account.iloc[0]['id']
        
        # Get performance metrics
        perf_query = """
        SELECT * FROM leaderboard 
        WHERE account_id = ?
        ORDER BY window_days
        """
        performance = pd.read_sql_query(perf_query, self.conn, params=(account_id,))
        
        # Get recent signals
        signals_query = """
        SELECT 
            s.*,
            p.posted_at,
            p.text,
            o.realized_return,
            o.won
        FROM signals s
        JOIN posts p ON s.post_id = p.id
        LEFT JOIN outcomes o ON s.id = o.signal_id
        WHERE s.account_id = ?
        ORDER BY p.posted_at DESC
        LIMIT 100
        """
        signals = pd.read_sql_query(signals_query, self.conn, params=(account_id,))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'html':
            # Generate HTML report
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Performance Report - @{account_handle}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #333; }}
                    h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .metric {{ display: inline-block; margin: 10px 20px; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
                    .metric-label {{ color: #666; }}
                </style>
            </head>
            <body>
                <h1>Performance Report: @{account_handle}</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>Account Summary</h2>
                <div>
                    <div class="metric">
                        <div class="metric-value">{account.iloc[0]['category']}</div>
                        <div class="metric-label">Category</div>
                    </div>
                </div>
                
                <h2>Performance Metrics</h2>
                <table>
                    <tr>
                        <th>Window</th>
                        <th>Signals</th>
                        <th>Win Rate</th>
                        <th>Excess Return</th>
                        <th>Alpha Score</th>
                    </tr>
            """
            
            for _, row in performance.iterrows():
                win_rate = f"{row['win_rate']*100:.1f}%" if pd.notna(row['win_rate']) else "-"
                excess = f"{row['mean_excess_return']*100:.2f}%" if pd.notna(row['mean_excess_return']) else "-"
                
                html_content += f"""
                    <tr>
                        <td>{row['window_days']} days</td>
                        <td>{row['n_signals']}</td>
                        <td>{win_rate}</td>
                        <td>{excess}</td>
                        <td>{row['alpha_score']:.3f}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                
                <h2>Recent Signals</h2>
                <p>Last 100 signals</p>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Asset Class</th>
                        <th>Instrument</th>
                        <th>Side</th>
                        <th>Result</th>
                    </tr>
            """
            
            for _, sig in signals.head(20).iterrows():
                result = "✅" if sig['won'] == 1 else "❌" if sig['won'] == 0 else "⏳"
                html_content += f"""
                    <tr>
                        <td>{sig['posted_at']}</td>
                        <td>{sig['asset_class']}</td>
                        <td>{sig['instrument'] or sig['market_ref'] or '-'}</td>
                        <td>{sig['side']}</td>
                        <td>{result}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </body>
            </html>
            """
            
            path = self.export_dir / f"report_{account_handle}_{timestamp}.html"
            with open(path, 'w') as f:
                f.write(html_content)
            
            return path
        
        elif format == 'json':
            report = {
                'account': account.to_dict('records')[0],
                'performance': performance.to_dict('records'),
                'recent_signals': signals.head(100).to_dict('records')
            }
            
            path = self.export_dir / f"report_{account_handle}_{timestamp}.json"
            with open(path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            return path
    
    def export_discovery_candidates(self, min_signals: int = 5, 
                                   min_alpha: float = 0.5):
        """Export list of high-potential accounts for monitoring."""
        query = """
        SELECT 
            a.handle,
            a.category,
            l.n_signals,
            l.alpha_score,
            l.win_rate,
            l.mean_excess_return
        FROM leaderboard l
        JOIN accounts a ON l.account_id = a.id
        WHERE l.n_signals >= ?
        AND l.alpha_score >= ?
        AND l.window_days = 90
        ORDER BY l.alpha_score DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(min_signals, min_alpha))
        
        timestamp = datetime.now().strftime('%Y%m%d')
        path = self.export_dir / f"discovery_candidates_{timestamp}.csv"
        df.to_csv(path, index=False)
        
        return path

def main():
    """CLI for data export."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export Alpha Tracker data')
    parser.add_argument('--type', choices=['leaderboard', 'signals', 'report', 'discovery'],
                       required=True, help='Export type')
    parser.add_argument('--format', choices=['csv', 'json', 'excel', 'html'],
                       default='csv', help='Output format')
    parser.add_argument('--account', help='Account handle for filtering')
    parser.add_argument('--asset-class', help='Asset class filter')
    parser.add_argument('--days', type=int, default=30, help='Days to look back')
    parser.add_argument('--window', type=int, default=90, help='Leaderboard window')
    
    args = parser.parse_args()
    
    db_path = BASE / 'alpha_tracker.db'
    exporter = DataExporter(db_path)
    
    if args.type == 'leaderboard':
        path = exporter.export_leaderboard(args.window, args.format)
    elif args.type == 'signals':
        path = exporter.export_signals(args.account, args.asset_class, 
                                      args.days, args.format)
    elif args.type == 'report' and args.account:
        path = exporter.export_performance_report(args.account, args.format)
    elif args.type == 'discovery':
        path = exporter.export_discovery_candidates()
    else:
        print("Invalid arguments")
        return
    
    print(f"Export complete: {path}")

if __name__ == "__main__":
    main()


