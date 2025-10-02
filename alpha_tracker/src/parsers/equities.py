"""Enhanced equity signal parser with improved pattern recognition."""
import re
from typing import List, Optional, Tuple
from .base import ParsedSignal

# Common equity ticker patterns
TICKER_PATTERN = r'\$([A-Z]{1,5})\b'
TICKER_ALT_PATTERN = r'\b([A-Z]{2,5})\b(?:\s+(?:calls?|puts?|shares?|stock))?'

# Action patterns with confidence extraction
BUY_PATTERNS = [
    r'(?:buy|long|bought|buying|accumulate|bullish|add(?:ing)?)\s+(?:on\s+)?',
    r'(?:entry|enter(?:ed|ing)?|position)\s+(?:at|in|on)\s+',
    r'(?:target|pt|price\s+target)[:=\s]+\$?(\d+(?:\.\d+)?)',
]

SELL_PATTERNS = [
    r'(?:sell|short|sold|selling|dump|bearish|exit(?:ed|ing)?)\s+(?:on\s+)?',
    r'(?:close|closing|closed)\s+(?:position|trade)\s+(?:in|on)\s+',
    r'(?:stop|sl|stop\s+loss)[:=\s]+\$?(\d+(?:\.\d+)?)',
]

# Confidence/conviction patterns
CONFIDENCE_PATTERNS = [
    (r'(\d+)%\s+(?:confidence|conviction|certain|sure)', lambda m: float(m.group(1))/100),
    (r'(?:very\s+)?(?:high|strong)\s+(?:confidence|conviction)', lambda m: 0.85),
    (r'(?:medium|moderate)\s+(?:confidence|conviction)', lambda m: 0.65),
    (r'(?:low|weak)\s+(?:confidence|conviction)', lambda m: 0.35),
    (r'(?:starter|small)\s+(?:position|size)', lambda m: 0.40),
    (r'(?:full|large)\s+(?:position|size)', lambda m: 0.80),
]

# Time horizon patterns
HORIZON_PATTERNS = [
    (r'(?:day|intraday)\s+trade', 86400),  # 1 day
    (r'(?:swing|week)\s+trade', 604800),  # 1 week
    (r'(?:monthly?|30\s*day)', 2592000),  # 30 days
    (r'(?:quarterly?|90\s*day|3\s*month)', 7776000),  # 90 days
    (r'(?:yearly?|annual|12\s*month)', 31536000),  # 1 year
    (r'(?:by|before|until)\s+(?:eod|close)', 28800),  # ~8 hours
]

# Price target patterns
TARGET_PATTERNS = [
    r'(?:pt|target|tp)[:=\s]+\$?(\d+(?:\.\d+)?)',
    r'\$?(\d+(?:\.\d+)?)\s+(?:target|pt)',
    r'(?:see(?:ing)?|expect(?:ing)?)\s+\$?(\d+(?:\.\d+)?)',
]

def extract_ticker(text: str) -> Optional[str]:
    """Extract the most prominent ticker from text."""
    # Try $ prefix first
    match = re.search(TICKER_PATTERN, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Try context-based extraction
    for pattern in BUY_PATTERNS + SELL_PATTERNS:
        full_pattern = pattern + TICKER_ALT_PATTERN
        match = re.search(full_pattern, text, re.IGNORECASE)
        if match and hasattr(match, 'groups') and match.groups():
            ticker = match.group(len(match.groups()))
            if ticker and 2 <= len(ticker) <= 5:
                return ticker.upper()
    
    # Fallback to any uppercase sequence
    match = re.search(r'\b([A-Z]{2,5})\b', text)
    if match:
        ticker = match.group(1)
        # Filter out common non-ticker words
        if ticker not in {'THE', 'AND', 'FOR', 'WITH', 'FROM', 'THIS', 'THAT', 'USA', 'CEO'}:
            return ticker
    
    return None

def extract_side(text: str) -> Optional[str]:
    """Determine if the signal is buy/long or sell/short."""
    text_lower = text.lower()
    
    # Count buy vs sell signals
    buy_score = sum(1 for pattern in BUY_PATTERNS if re.search(pattern, text_lower))
    sell_score = sum(1 for pattern in SELL_PATTERNS if re.search(pattern, text_lower))
    
    # Look for explicit directional words
    if any(word in text_lower for word in ['bullish', 'long', 'buy', 'bought', 'accumulate']):
        buy_score += 2
    if any(word in text_lower for word in ['bearish', 'short', 'sell', 'sold', 'dump']):
        sell_score += 2
    
    # Look for options context
    if 'call' in text_lower or 'calls' in text_lower:
        buy_score += 1
    if 'put' in text_lower or 'puts' in text_lower:
        sell_score += 1
    
    if buy_score > sell_score:
        return 'long'
    elif sell_score > buy_score:
        return 'short'
    
    # Default to long for neutral mentions with targets
    if re.search(r'(?:pt|target|tp)[:=\s]+\$?\d+', text_lower):
        return 'long'
    
    return None

def extract_confidence(text: str) -> Optional[float]:
    """Extract confidence level from text."""
    text_lower = text.lower()
    
    for pattern, extractor in CONFIDENCE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return extractor(match)
    
    # Look for position sizing hints
    if 'starter' in text_lower or 'small position' in text_lower:
        return 0.40
    if 'full position' in text_lower or 'all in' in text_lower:
        return 0.85
    
    # Look for hedging language
    hedging_words = ['maybe', 'perhaps', 'might', 'could', 'possibly']
    strong_words = ['definitely', 'certainly', 'surely', 'absolutely']
    
    hedging_count = sum(1 for word in hedging_words if word in text_lower)
    strong_count = sum(1 for word in strong_words if word in text_lower)
    
    if strong_count > hedging_count:
        return 0.75
    elif hedging_count > strong_count:
        return 0.45
    
    return None

def extract_horizon(text: str) -> Optional[int]:
    """Extract time horizon in seconds."""
    text_lower = text.lower()
    
    for pattern, seconds in HORIZON_PATTERNS:
        if re.search(pattern, text_lower):
            return seconds
    
    # Check for specific date mentions
    import re
    from datetime import datetime, timedelta
    
    # Try to find "by Friday", "by month end", etc.
    weekday_match = re.search(r'by\s+(monday|tuesday|wednesday|thursday|friday)', text_lower)
    if weekday_match:
        # Approximate - return 3 days
        return 259200
    
    # Default based on context
    if 'today' in text_lower or 'intraday' in text_lower:
        return 86400
    elif 'this week' in text_lower:
        return 604800
    
    return None

def extract_price_info(text: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract entry, target, and stop prices."""
    entry = None
    target = None
    stop = None
    
    # Extract target
    for pattern in TARGET_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                target = float(match.group(1))
                break
            except:
                pass
    
    # Extract stop loss
    stop_patterns = [
        r'(?:stop|sl|stop\s+loss)[:=\s]+\$?(\d+(?:\.\d+)?)',
        r'(?:risk|risking)\s+(?:to|at)\s+\$?(\d+(?:\.\d+)?)',
    ]
    for pattern in stop_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                stop = float(match.group(1))
                break
            except:
                pass
    
    # Extract entry
    entry_patterns = [
        r'(?:entry|enter|buy|long)\s+(?:at|@|around)\s+\$?(\d+(?:\.\d+)?)',
        r'(?:bought|entered)\s+(?:at|@)\s+\$?(\d+(?:\.\d+)?)',
        r'\$?(\d+(?:\.\d+)?)\s+(?:entry|buy|long)\b',
    ]
    for pattern in entry_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                entry = float(match.group(1))
                break
            except:
                pass
    
    return entry, target, stop

def extract_size(text: str) -> Optional[float]:
    """Extract position size or dollar amount."""
    text_lower = text.lower()
    
    # Look for percentage of portfolio
    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s+(?:of\s+)?(?:portfolio|account|capital)', text_lower)
    if pct_match:
        return float(pct_match.group(1)) / 100
    
    # Look for dollar amounts
    dollar_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d+)?)[kmb]?\b', text_lower)
    if dollar_match:
        amount_str = dollar_match.group(1).replace(',', '')
        amount = float(amount_str)
        # Normalize large amounts
        if text_lower[dollar_match.end()-1:dollar_match.end()] == 'k':
            amount *= 1000
        elif text_lower[dollar_match.end()-1:dollar_match.end()] == 'm':
            amount *= 1000000
        elif text_lower[dollar_match.end()-1:dollar_match.end()] == 'b':
            amount *= 1000000000
        return amount
    
    # Look for share counts
    shares_match = re.search(r'(\d+(?:,\d{3})*)\s+(?:shares?|stocks?)', text_lower)
    if shares_match:
        return float(shares_match.group(1).replace(',', ''))
    
    return None

def parse_equity(text: str) -> List[ParsedSignal]:
    """Parse equity trading signals from text."""
    signals = []
    
    ticker = extract_ticker(text)
    if not ticker:
        return signals
    
    side = extract_side(text)
    if not side:
        # Try to infer from context
        if '$' + ticker in text:
            side = 'long'  # Default for mentioned tickers
        else:
            return signals
    
    confidence = extract_confidence(text)
    horizon = extract_horizon(text)
    entry, target, stop = extract_price_info(text)
    size = extract_size(text)
    
    # Create the signal
    signal = ParsedSignal(
        asset_class='equity',
        instrument=ticker,
        market_ref=None,
        side=side,
        confidence=confidence,
        horizon_seconds=horizon,
        size=size,
        extracted={
            'entry_price': entry,
            'target_price': target,
            'stop_price': stop,
            'raw_text': text[:500]  # Store first 500 chars for reference
        }
    )
    
    signals.append(signal)
    
    # Check for multiple tickers
    all_tickers = re.findall(TICKER_PATTERN, text)
    if len(all_tickers) > 1:
        for other_ticker in all_tickers:
            if other_ticker.upper() != ticker:
                signals.append(ParsedSignal(
            asset_class='equity',
                    instrument=other_ticker.upper(),
            market_ref=None,
                    side=side,
                    confidence=confidence,
                    horizon_seconds=horizon,
                    size=size,
                    extracted={'raw_text': text[:500]}
                ))
    
    return signals