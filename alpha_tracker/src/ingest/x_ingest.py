"""X (Twitter) post ingestion module with enhanced capabilities."""
import pandas as pd
import json
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests
from pathlib import Path

# Alpha account discovery patterns
DISCOVERY_PATTERNS = {
    'equity': [
        r'\$[A-Z]{1,5}\b',  # Stock tickers
        r'(?:buy|sell|long|short|calls?|puts?)',
        r'(?:pt|target|stop|sl)[:=]\s*\$?\d+',
    ],
    'crypto': [
        r'\$(?:BTC|ETH|SOL|AVAX|ARB|OP|INJ|TIA)',
        r'(?:leverage|perp|futures|spot)',
        r'(?:moon|pump|dump|hodl)',
    ],
    'prediction': [
        r'(?:polymarket|manifold|metaculus|kalshi)',
        r'(?:yes|no)\s+(?:at|@)\s*\d+[c%]',
        r'(?:bet|wager|position)',
    ],
    'sports': [
        r'(?:nfl|nba|mlb|nhl|ncaa)',
        r'[\+\-]\d+(?:\.\d)?(?:\s+units?)?',
        r'(?:over|under|spread|ml|moneyline)',
    ]
}

def load_posts_from_csv(filepath: str | Path) -> pd.DataFrame:
    """Load posts from CSV with validation."""
    df = pd.read_csv(filepath)
    
    # Required columns
    required = ['platform', 'handle', 'posted_at', 'text']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Add defaults
    if 'post_id' not in df.columns:
        df['post_id'] = df.index.astype(str)
    if 'category' not in df.columns:
        df['category'] = df.apply(lambda r: detect_category(r['text']), axis=1)
    if 'url' not in df.columns:
        df['url'] = df.apply(lambda r: f"https://x.com/{r['handle']}/status/{r['post_id']}", axis=1)
    
    # Validate dates
    df['posted_at'] = pd.to_datetime(df['posted_at'])
    
    return df

def detect_category(text: str) -> str:
    """Detect account category from post content."""
    scores = {}
    
    for category, patterns in DISCOVERY_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        scores[category] = score
    
    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    
    return 'general'

class XAPIClient:
    """X API v2 client for fetching posts."""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "AlphaTracker/1.0"
        }
    
    def get_user_id(self, username: str) -> Optional[str]:
        """Get user ID from username."""
        url = f"{self.base_url}/users/by/username/{username}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()['data']['id']
        except:
            pass
        return None
    
    def get_user_tweets(self, user_id: str, max_results: int = 100, 
                       start_time: Optional[datetime] = None) -> List[Dict]:
        """Fetch recent tweets from a user."""
        url = f"{self.base_url}/users/{user_id}/tweets"
        
        params = {
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,conversation_id,public_metrics,entities',
            'exclude': 'retweets,replies'
        }
        
        if start_time:
            params['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        tweets = []
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    tweets = data['data']
        except Exception as e:
            print(f"Error fetching tweets: {e}")
        
        return tweets
    
    def search_tweets(self, query: str, max_results: int = 100) -> List[Dict]:
        """Search for tweets matching query."""
        url = f"{self.base_url}/tweets/search/recent"
        
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,conversation_id,public_metrics'
        }
        
        tweets = []
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    tweets = data['data']
        except Exception as e:
            print(f"Error searching tweets: {e}")
        
        return tweets

def discover_alpha_accounts(bearer_token: str, search_terms: List[str], 
                           min_engagement: int = 100) -> pd.DataFrame:
    """Discover potential alpha accounts based on search terms."""
    client = XAPIClient(bearer_token)
    discovered = []
    
    for term in search_terms:
        tweets = client.search_tweets(term, max_results=100)
        
        for tweet in tweets:
            metrics = tweet.get('public_metrics', {})
            engagement = (metrics.get('retweet_count', 0) + 
                        metrics.get('like_count', 0) + 
                        metrics.get('reply_count', 0) * 2)
            
            if engagement >= min_engagement:
                discovered.append({
                    'author_id': tweet['author_id'],
                    'tweet_id': tweet['id'],
                    'text': tweet['text'],
                    'created_at': tweet['created_at'],
                    'engagement': engagement,
                    'search_term': term
                })
    
    if discovered:
        df = pd.DataFrame(discovered)
        # Group by author to find most active
        author_stats = df.groupby('author_id').agg({
            'tweet_id': 'count',
            'engagement': 'mean'
        }).rename(columns={'tweet_id': 'tweet_count', 'engagement': 'avg_engagement'})
        
        return author_stats.sort_values('avg_engagement', ascending=False)
    
    return pd.DataFrame()

def fetch_recent_posts_from_x(bearer_token: str, handles: List[str], 
                            hours_back: int = 24) -> pd.DataFrame:
    """Fetch recent posts from X for specified handles."""
    client = XAPIClient(bearer_token)
    posts = []
    
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    for handle in handles:
        # Remove @ if present
        username = handle.replace('@', '')
        
        # Get user ID
        user_id = client.get_user_id(username)
        if not user_id:
            print(f"Could not find user: {username}")
            continue
        
        # Get recent tweets
        tweets = client.get_user_tweets(user_id, start_time=start_time)
        
        for tweet in tweets:
            posts.append({
                'platform': 'x',
                'handle': username,
                'post_id': tweet['id'],
                'posted_at': tweet['created_at'],
                'text': tweet['text'],
                'url': f"https://x.com/{username}/status/{tweet['id']}",
                'raw': json.dumps(tweet)
            })
    
    if posts:
        df = pd.DataFrame(posts)
        df['posted_at'] = pd.to_datetime(df['posted_at'])
        df['category'] = df['text'].apply(detect_category)
        return df
    
    return pd.DataFrame()

def score_post_quality(text: str, category: str) -> float:
    """Score post quality for alpha potential."""
    score = 0.0
    
    # Check for specific signals
    if category == 'equity':
        if re.search(r'\$[A-Z]{1,5}\b', text):
            score += 0.2
        if re.search(r'(?:pt|target)[:=]\s*\$?\d+', text, re.IGNORECASE):
            score += 0.3
        if re.search(r'(?:buy|long|bullish)', text, re.IGNORECASE):
            score += 0.2
    
    elif category == 'crypto':
        if re.search(r'\$(?:BTC|ETH|SOL)', text):
            score += 0.2
        if re.search(r'\d+x\s*(?:leverage|lev)', text, re.IGNORECASE):
            score += 0.2
        if re.search(r'(?:entry|tp|sl)[:=]\s*\$?\d+', text, re.IGNORECASE):
            score += 0.3
    
    elif category == 'prediction':
        if re.search(r'polymarket|manifold', text, re.IGNORECASE):
            score += 0.3
        if re.search(r'\d+[%c]', text):
            score += 0.2
    
    elif category == 'sports':
        if re.search(r'[\+\-]\d+(?:\.\d)?', text):
            score += 0.3
        if re.search(r'\d+(?:\.\d)?\s*units?', text, re.IGNORECASE):
            score += 0.2
    
    # Check for confidence indicators
    if re.search(r'(?:high|strong|love|hammer|max)', text, re.IGNORECASE):
        score += 0.1
    
    # Check for track record mentions
    if re.search(r'\d+\-\d+', text):  # e.g., "15-3"
        score += 0.15
    
    # Penalize vague posts
    if not re.search(r'(?:\$|%|\d+)', text):
        score *= 0.5
    
    return min(score, 1.0)

def filter_alpha_posts(df: pd.DataFrame, min_quality: float = 0.3) -> pd.DataFrame:
    """Filter posts for alpha quality."""
    if df.empty:
        return df
    
    df['quality_score'] = df.apply(
        lambda r: score_post_quality(r['text'], r.get('category', 'general')), 
        axis=1
    )
    
    # Filter by quality
    filtered = df[df['quality_score'] >= min_quality].copy()
    
    # Sort by quality and recency
    filtered = filtered.sort_values(['quality_score', 'posted_at'], 
                                   ascending=[False, False])
    
    return filtered

# Mock function for demo/testing
def generate_sample_posts(n: int = 10) -> pd.DataFrame:
    """Generate sample posts for testing."""
    from datetime import datetime, timedelta
    import random
    
    samples = [
        ("fintwit_alpha", "equity", "$AAPL PT raised to $195. Strong iPhone demand in China. Entry at $188, SL $185. High conviction play."),
        ("crypto_whale", "crypto", "$SOL looking bullish above $100. 3x leverage long, TP1 $115, TP2 $125, SL $95. DYOR"),
        ("sports_sharp", "sports", "NFL: Chiefs -3.5 vs Bills. Max play 5u. KC defense elite at home, 8-1 ATS last 9."),
        ("prediction_pro", "prediction", "Polymarket: Biden approval >45% by March. Currently 38%. Buying YES at 42c. Economic data improving."),
        ("options_flow", "equity", "$NVDA unusual call activity. March $800 calls swept at ask. Following the smart money here."),
        ("btc_maximalist", "crypto", "BTC forming bullish flag on 4H. Long entry $65k, targeting $72k. Stop below $63k. 2x leverage."),
        ("nba_analytics", "sports", "Lakers/Celtics O227.5. Both teams top-10 pace, weak perimeter D. 3 units."),
        ("macro_trader", "equity", "$SPY puts for hedge. VIX too low given geopolitical risks. 450P expiring Friday."),
        ("defi_farmer", "crypto", "$ARB ecosystem plays. Long ARB at $1.85, also accumulating GMX and MAGIC. 6-month hold."),
        ("election_trader", "prediction", "Manifold: Trump wins NH primary >70%. Current 64%. Demographics favor him, buying YES.")
    ]
    
    posts = []
    base_time = datetime.utcnow()
    
    for i in range(min(n, len(samples))):
        handle, category, text = samples[i % len(samples)]
        posts.append({
            'platform': 'x',
            'handle': handle,
            'post_id': f"mock_{i}",
            'posted_at': base_time - timedelta(hours=random.randint(1, 72)),
            'text': text,
            'category': category,
            'url': f"https://x.com/{handle}/status/mock_{i}"
        })
    
    df = pd.DataFrame(posts)
    df['posted_at'] = pd.to_datetime(df['posted_at'])
    return df