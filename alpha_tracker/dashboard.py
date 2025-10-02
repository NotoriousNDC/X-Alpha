"""Streamlit dashboard for Alpha Tracker visualization."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import sys

# Add src to path
BASE = Path(__file__).resolve().parent
sys.path.append(str(BASE))

from src.db import get_conn

# Page config
st.set_page_config(
    page_title="Alpha Tracker Dashboard",
    page_icon="📈",
    layout="wide"
)

@st.cache_resource
def get_database_connection():
    """Get cached database connection."""
    return get_conn(BASE / 'alpha_tracker.db')

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_leaderboard():
    """Load leaderboard data."""
    conn = get_database_connection()
    query = """
    SELECT l.*, a.handle, a.category 
    FROM leaderboard l 
    JOIN accounts a ON l.account_id = a.id 
    ORDER BY l.alpha_score DESC
    """
    return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def load_signals_with_outcomes():
    """Load signals with their outcomes."""
    conn = get_database_connection()
    query = """
    SELECT 
        s.*, 
        a.handle,
        o.realized_return,
        o.excess_return,
        o.won,
        o.clv_points,
        o.pnl_per_contract
    FROM signals s
    JOIN accounts a ON s.account_id = a.id
    LEFT JOIN outcomes o ON s.id = o.signal_id
    ORDER BY s.id DESC
    LIMIT 500
    """
    return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def load_account_performance(account_id):
    """Load detailed performance for an account."""
    conn = get_database_connection()
    query = """
    SELECT 
        s.*,
        o.realized_return,
        o.excess_return,
        o.won,
        o.clv_points,
        o.pnl_per_contract,
        o.settled_at
    FROM signals s
    LEFT JOIN outcomes o ON s.id = o.signal_id
    WHERE s.account_id = ?
    ORDER BY s.id DESC
    """
    return pd.read_sql_query(query, conn, params=(account_id,))

def main():
    st.title("🎯 Alpha Tracker Dashboard")
    st.markdown("Track and score alpha-leaking accounts across equities, crypto, prediction markets, and sports betting")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Load data
    leaderboard = load_leaderboard()
    signals = load_signals_with_outcomes()
    
    # Time window filter
    window_options = st.sidebar.selectbox(
        "Time Window",
        options=[7, 30, 90, 180, 365],
        index=2,
        format_func=lambda x: f"Last {x} days"
    )
    
    # Asset class filter
    asset_classes = ['All'] + list(signals['asset_class'].dropna().unique())
    selected_asset = st.sidebar.selectbox("Asset Class", asset_classes)
    
    # Category filter
    if not leaderboard.empty:
        categories = ['All'] + list(leaderboard['category'].dropna().unique())
        selected_category = st.sidebar.selectbox("Account Category", categories)
    
    # Main content
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Leaderboard", "📈 Signals", "👤 Account Details", "📉 Analytics", "🔍 Discovery"])
    
    with tab1:
        st.header("Alpha Leaderboard")
        
        # Filter leaderboard
        filtered_lb = leaderboard.copy()
        if selected_category != 'All':
            filtered_lb = filtered_lb[filtered_lb['category'] == selected_category]
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Accounts", len(filtered_lb))
        with col2:
            active_accounts = len(filtered_lb[filtered_lb['n_signals'] > 0])
            st.metric("Active Accounts", active_accounts)
        with col3:
            if not filtered_lb.empty:
                avg_alpha = filtered_lb['alpha_score'].mean()
                st.metric("Avg Alpha Score", f"{avg_alpha:.3f}")
        with col4:
            total_signals = filtered_lb['n_signals'].sum()
            st.metric("Total Signals", int(total_signals))
        
        # Leaderboard table
        st.subheader("Top Alpha Accounts")
        
        # Format display
        display_cols = ['handle', 'category', 'n_signals', 'win_rate', 
                       'mean_excess_return', 'sharpe_like', 'alpha_score']
        
        if not filtered_lb.empty:
            display_df = filtered_lb[display_cols].copy()
            display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "-")
            display_df['mean_excess_return'] = display_df['mean_excess_return'].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "-")
            display_df['sharpe_like'] = display_df['sharpe_like'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
            display_df['alpha_score'] = display_df['alpha_score'].apply(lambda x: f"{x:.3f}")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "handle": "Account",
                    "category": "Category",
                    "n_signals": "Signals",
                    "win_rate": "Win Rate",
                    "mean_excess_return": "Excess Return",
                    "sharpe_like": "Sharpe",
                    "alpha_score": st.column_config.NumberColumn("Alpha Score", format="%.3f")
                }
            )
    
    with tab2:
        st.header("Recent Signals")
        
        # Filter signals
        filtered_signals = signals.copy()
        if selected_asset != 'All':
            filtered_signals = filtered_signals[filtered_signals['asset_class'] == selected_asset]
        
        # Signal statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sigs = len(filtered_signals)
            st.metric("Total Signals", total_sigs)
        with col2:
            with_outcomes = filtered_signals['won'].notna().sum()
            st.metric("Settled", with_outcomes)
        with col3:
            if with_outcomes > 0:
                win_rate = filtered_signals['won'].mean()
                st.metric("Overall Win Rate", f"{win_rate*100:.1f}%")
        with col4:
            if filtered_signals['excess_return'].notna().any():
                avg_excess = filtered_signals['excess_return'].mean()
                st.metric("Avg Excess Return", f"{avg_excess*100:.2f}%")
        
        # Signals table
        st.subheader("Signal Details")
        
        signal_cols = ['handle', 'asset_class', 'instrument', 'side', 
                      'confidence', 'won', 'excess_return']
        
        if not filtered_signals.empty:
            display_sigs = filtered_signals[signal_cols].head(100).copy()
            display_sigs['confidence'] = display_sigs['confidence'].apply(lambda x: f"{x*100:.0f}%" if pd.notna(x) else "-")
            display_sigs['won'] = display_sigs['won'].apply(lambda x: "✅" if x==1 else "❌" if x==0 else "⏳")
            display_sigs['excess_return'] = display_sigs['excess_return'].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "-")
            
            st.dataframe(
                display_sigs,
                use_container_width=True,
                hide_index=True
            )
    
    with tab3:
        st.header("Account Deep Dive")
        
        # Account selector
        if not leaderboard.empty:
            account_options = leaderboard[['account_id', 'handle']].set_index('account_id')['handle'].to_dict()
            selected_account = st.selectbox(
                "Select Account",
                options=list(account_options.keys()),
                format_func=lambda x: account_options[x]
            )
            
            if selected_account:
                # Load account performance
                account_perf = load_account_performance(selected_account)
                account_info = leaderboard[leaderboard['account_id'] == selected_account].iloc[0]
                
                # Account header
                st.subheader(f"@{account_info['handle']}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Alpha Score", f"{account_info['alpha_score']:.3f}")
                with col2:
                    st.metric("Total Signals", int(account_info['n_signals']))
                with col3:
                    if pd.notna(account_info['win_rate']):
                        st.metric("Win Rate", f"{account_info['win_rate']*100:.1f}%")
                with col4:
                    if pd.notna(account_info['mean_excess_return']):
                        st.metric("Excess Return", f"{account_info['mean_excess_return']*100:.2f}%")
                
                # Performance chart
                if not account_perf.empty and account_perf['excess_return'].notna().any():
                    st.subheader("Performance Over Time")
                    
                    perf_data = account_perf[account_perf['excess_return'].notna()].copy()
                    perf_data['cumulative_return'] = (1 + perf_data['excess_return']).cumprod() - 1
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=perf_data.index,
                        y=perf_data['cumulative_return'] * 100,
                        mode='lines+markers',
                        name='Cumulative Excess Return',
                        line=dict(color='green' if perf_data['cumulative_return'].iloc[-1] > 0 else 'red')
                    ))
                    fig.update_layout(
                        yaxis_title="Cumulative Return (%)",
                        xaxis_title="Signal #",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Signal breakdown by asset class
                if not account_perf.empty:
                    st.subheader("Signal Breakdown")
                    
                    breakdown = account_perf.groupby('asset_class').agg({
                        'id': 'count',
                        'won': lambda x: x.mean() if x.notna().any() else None,
                        'excess_return': lambda x: x.mean() if x.notna().any() else None
                    }).rename(columns={'id': 'count'})
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.pie(
                            values=breakdown['count'],
                            names=breakdown.index,
                            title="Signals by Asset Class"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if breakdown['won'].notna().any():
                            fig = px.bar(
                                x=breakdown.index,
                                y=breakdown['won'] * 100,
                                title="Win Rate by Asset Class",
                                labels={'y': 'Win Rate (%)'}
                            )
                            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Analytics & Insights")
        
        # Performance distribution
        col1, col2 = st.columns(2)
        
        with col1:
            if not leaderboard.empty and leaderboard['alpha_score'].notna().any():
                st.subheader("Alpha Score Distribution")
                fig = px.histogram(
                    leaderboard[leaderboard['alpha_score'].notna()],
                    x='alpha_score',
                    nbins=20,
                    title="Distribution of Alpha Scores"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if not signals.empty and signals['excess_return'].notna().any():
                st.subheader("Return Distribution")
                fig = px.histogram(
                    signals[signals['excess_return'].notna()],
                    x='excess_return',
                    nbins=30,
                    title="Distribution of Excess Returns"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Category performance
        if not leaderboard.empty:
            st.subheader("Performance by Category")
            
            cat_perf = leaderboard.groupby('category').agg({
                'alpha_score': 'mean',
                'win_rate': lambda x: x.mean() if x.notna().any() else None,
                'mean_excess_return': lambda x: x.mean() if x.notna().any() else None,
                'n_signals': 'sum'
            }).round(4)
            
            st.dataframe(cat_perf, use_container_width=True)
        
        # Time-based analysis
        st.subheader("Signal Activity Over Time")
        
        if not signals.empty:
            # This would need created_at timestamp in signals table
            st.info("Time-series analysis requires signal timestamps. Add 'created_at' to signals table for this feature.")
    
    with tab5:
        st.header("Account Discovery")
        
        st.markdown("""
        ### Discovery Methods
        
        1. **Engagement-based**: Find accounts with high engagement on alpha-related content
        2. **Network-based**: Analyze who top performers follow/interact with
        3. **Content-based**: Search for specific patterns in posts
        4. **Performance-based**: Track accounts mentioned by existing top performers
        """)
        
        # Discovery search
        st.subheader("Search Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_terms = st.text_area(
                "Search Terms (one per line)",
                value="$SPY calls\npolymarket odds\nNFL spread\n$BTC target",
                height=100
            )
            
            min_engagement = st.number_input(
                "Minimum Engagement",
                min_value=0,
                value=100,
                step=50
            )
        
        with col2:
            search_category = st.selectbox(
                "Focus Category",
                ["All", "equity", "crypto", "prediction", "sports"]
            )
            
            lookback_days = st.number_input(
                "Lookback Days",
                min_value=1,
                max_value=30,
                value=7
            )
        
        if st.button("🔍 Discover Accounts"):
            st.info("Account discovery requires X API credentials. Configure in environment variables.")
            
            # Placeholder for discovery results
            st.subheader("Discovery Results")
            
            # Mock results for demo
            mock_discoveries = pd.DataFrame({
                'Handle': ['@newtrader1', '@cryptowhale99', '@sharpbettor'],
                'Category': ['equity', 'crypto', 'sports'],
                'Avg Engagement': [245, 512, 189],
                'Recent Signals': [5, 12, 8],
                'Sample Post': [
                    "$TSLA 900C sweep detected...",
                    "$SOL breakout confirmed, targeting...",
                    "Chiefs -3 is a gift, hammer it..."
                ]
            })
            
            st.dataframe(mock_discoveries, use_container_width=True, hide_index=True)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### About
    Alpha Tracker analyzes and scores accounts that share trading/betting signals across multiple asset classes.
    
    **Metrics:**
    - Win Rate
    - Excess Returns
    - Sharpe Ratio
    - CLV (Sports)
    - Brier Score (Predictions)
    
    **Data Sources:**
    - X (Twitter) API
    - Market data feeds
    - Prediction market APIs
    - Sports odds providers
    """)

if __name__ == "__main__":
    main()


