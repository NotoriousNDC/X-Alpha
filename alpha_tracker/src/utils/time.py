"""Time and date utilities for Alpha Tracker."""
from datetime import datetime, timedelta
import pytz
from typing import Optional, Tuple

def parse_timeframe(text: str) -> Optional[int]:
    """Parse timeframe from text to seconds.
    
    Examples:
        '1d' -> 86400
        '1w' -> 604800
        '30d' -> 2592000
    """
    text = text.lower().strip()
    
    # Direct mappings
    mappings = {
        'today': 86400,
        'tomorrow': 172800,
        'week': 604800,
        'month': 2592000,
        'quarter': 7776000,
        'year': 31536000
    }
    
    if text in mappings:
        return mappings[text]
    
    # Parse patterns like "1d", "2w", etc.
    import re
    match = re.match(r'(\d+)([dwmyh])', text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'h': 3600,      # hours
            'd': 86400,     # days
            'w': 604800,    # weeks
            'm': 2592000,   # months (30 days)
            'y': 31536000   # years
        }
        
        return value * multipliers.get(unit, 0)
    
    return None

def market_hours(market: str = 'US') -> Tuple[datetime, datetime]:
    """Get market open and close times for today.
    
    Args:
        market: Market identifier ('US', 'EU', 'ASIA', 'CRYPTO')
    
    Returns:
        Tuple of (open_time, close_time) in UTC
    """
    now = datetime.now(pytz.UTC)
    today = now.date()
    
    if market == 'US':
        # NYSE hours: 9:30 AM - 4:00 PM ET
        tz = pytz.timezone('America/New_York')
        open_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=9, minute=30)))
        close_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=16)))
    
    elif market == 'EU':
        # LSE hours: 8:00 AM - 4:30 PM GMT
        tz = pytz.timezone('Europe/London')
        open_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=8)))
        close_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=16, minute=30)))
    
    elif market == 'ASIA':
        # Tokyo hours: 9:00 AM - 3:00 PM JST
        tz = pytz.timezone('Asia/Tokyo')
        open_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=9)))
        close_time = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=15)))
    
    elif market == 'CRYPTO':
        # 24/7 market
        return now, now + timedelta(days=1)
    
    else:
        raise ValueError(f"Unknown market: {market}")
    
    # Convert to UTC
    return open_time.astimezone(pytz.UTC), close_time.astimezone(pytz.UTC)

def is_market_open(market: str = 'US') -> bool:
    """Check if market is currently open."""
    if market == 'CRYPTO':
        return True  # Always open
    
    now = datetime.now(pytz.UTC)
    open_time, close_time = market_hours(market)
    
    return open_time <= now <= close_time

def next_market_open(market: str = 'US') -> datetime:
    """Get next market open time."""
    if market == 'CRYPTO':
        return datetime.now(pytz.UTC)  # Always open
    
    now = datetime.now(pytz.UTC)
    open_time, _ = market_hours(market)
    
    if now < open_time:
        return open_time
    else:
        # Next day
        tomorrow = now + timedelta(days=1)
        if market == 'US':
            # Skip weekends
            while tomorrow.weekday() >= 5:  # Saturday = 5, Sunday = 6
                tomorrow += timedelta(days=1)
        
        tomorrow_date = tomorrow.date()
        if market == 'US':
            tz = pytz.timezone('America/New_York')
            return tz.localize(datetime.combine(tomorrow_date, 
                             datetime.min.time().replace(hour=9, minute=30))).astimezone(pytz.UTC)
        # Add other markets as needed
    
    return open_time

def humanize_timedelta(td: timedelta) -> str:
    """Convert timedelta to human-readable string."""
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = total_seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"

def parse_horizon_from_text(text: str) -> Optional[int]:
    """Extract time horizon from text in seconds."""
    import re
    
    text_lower = text.lower()
    
    # Common patterns
    patterns = [
        (r'(\d+)\s*day', lambda x: int(x) * 86400),
        (r'(\d+)\s*week', lambda x: int(x) * 604800),
        (r'(\d+)\s*month', lambda x: int(x) * 2592000),
        (r'(\d+)\s*hour', lambda x: int(x) * 3600),
        (r'by\s+(?:end\s+of\s+)?(?:the\s+)?day', lambda x: 28800),  # ~8 hours
        (r'by\s+(?:end\s+of\s+)?(?:the\s+)?week', lambda x: 345600),  # ~4 days
        (r'intraday|day\s*trade', lambda x: 86400),
        (r'swing\s*trade', lambda x: 604800),
        (r'long[\s-]?term', lambda x: 31536000),
    ]
    
    for pattern, converter in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if match.groups():
                return converter(match.group(1))
            else:
                return converter(None)
    
    return None

def get_rolling_windows() -> list:
    """Get standard rolling window periods."""
    return [
        (1, "24 hours"),
        (7, "1 week"),
        (30, "30 days"),
        (90, "90 days"),
        (180, "6 months"),
        (365, "1 year")
    ]