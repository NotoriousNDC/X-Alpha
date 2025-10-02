"""Text processing utilities for Alpha Tracker."""
import re
from typing import List, Optional, Tuple, Dict
import hashlib

def clean_text(text: str) -> str:
    """Clean and normalize text for processing."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Fix common encoding issues
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text

def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from text."""
    return re.findall(r'@(\w+)', text)

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text."""
    return re.findall(r'#(\w+)', text)

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)

def extract_tickers(text: str) -> List[str]:
    """Extract stock/crypto tickers from text."""
    # $ prefix tickers
    dollar_tickers = re.findall(r'\$([A-Z]{1,6})\b', text)
    
    # Contextual tickers (near keywords)
    context_pattern = r'\b(?:buy|sell|long|short|bullish|bearish)\s+([A-Z]{2,5})\b'
    context_tickers = re.findall(context_pattern, text, re.IGNORECASE)
    
    # Combine and deduplicate
    all_tickers = list(set(dollar_tickers + [t.upper() for t in context_tickers]))
    
    # Filter out common words
    excluded = {'THE', 'AND', 'FOR', 'NOT', 'ALL', 'NEW', 'GET', 'SET'}
    return [t for t in all_tickers if t not in excluded]

def extract_numbers(text: str) -> List[float]:
    """Extract numeric values from text."""
    # Match various number formats
    patterns = [
        r'[-+]?\d*\.?\d+',  # Basic numbers
        r'\$\d+(?:,\d{3})*(?:\.\d+)?',  # Dollar amounts
        r'\d+(?:\.\d+)?%',  # Percentages
    ]
    
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Clean and convert
            cleaned = match.replace('$', '').replace(',', '').replace('%', '')
            try:
                numbers.append(float(cleaned))
            except ValueError:
                pass
    
    return numbers

def calculate_confidence_from_language(text: str) -> float:
    """Calculate confidence score based on language patterns."""
    text_lower = text.lower()
    confidence = 0.5  # Base confidence
    
    # Strong positive indicators
    strong_positive = [
        'definitely', 'certainly', 'absolutely', 'guaranteed',
        'lock', 'slam dunk', 'can\'t miss', 'sure thing',
        'max bet', 'all in', 'hammer', 'pound', 'love'
    ]
    
    # Moderate positive indicators
    moderate_positive = [
        'probably', 'likely', 'should', 'expect',
        'confident', 'bullish', 'like', 'decent'
    ]
    
    # Hedging/negative indicators
    hedging = [
        'maybe', 'perhaps', 'might', 'could', 'possibly',
        'risky', 'careful', 'small', 'starter', 'nibble'
    ]
    
    # Count indicators
    for phrase in strong_positive:
        if phrase in text_lower:
            confidence = max(confidence, 0.85)
            break
    
    for phrase in moderate_positive:
        if phrase in text_lower:
            confidence = max(confidence, 0.65)
    
    for phrase in hedging:
        if phrase in text_lower:
            confidence = min(confidence, 0.40)
    
    # Check for percentage confidence
    conf_match = re.search(r'(\d+)%\s*(?:confidence|sure|certain)', text_lower)
    if conf_match:
        stated_conf = float(conf_match.group(1)) / 100
        confidence = stated_conf
    
    return confidence

def tokenize_cashtags(text: str) -> Dict[str, List[str]]:
    """Tokenize and categorize cashtag mentions."""
    cashtags = {
        'stocks': [],
        'crypto': [],
        'forex': [],
        'unknown': []
    }
    
    # Known crypto symbols
    crypto_symbols = {
        'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'DOGE', 'XRP',
        'DOT', 'MATIC', 'LINK', 'UNI', 'AVAX', 'ATOM'
    }
    
    # Known forex pairs
    forex_patterns = ['EUR', 'GBP', 'JPY', 'USD', 'CAD', 'AUD', 'CHF']
    
    # Extract all cashtags
    all_cashtags = re.findall(r'\$([A-Z]{1,6})', text)
    
    for tag in all_cashtags:
        if tag in crypto_symbols:
            cashtags['crypto'].append(tag)
        elif any(fx in tag for fx in forex_patterns):
            cashtags['forex'].append(tag)
        elif len(tag) <= 4:  # Likely stock ticker
            cashtags['stocks'].append(tag)
        else:
            cashtags['unknown'].append(tag)
    
    return cashtags

def extract_sentiment_emoji(text: str) -> Dict[str, int]:
    """Extract and count sentiment-indicating emojis."""
    sentiment_emojis = {
        'bullish': ['🚀', '🌙', '📈', '💚', '🟢', '⬆️', '🔥', '💪', '🎯', '✅'],
        'bearish': ['📉', '🔴', '❌', '⬇️', '💔', '🩸', '😱', '⚠️', '🐻'],
        'neutral': ['🤔', '😐', '🤷', '📊', '💭', '⏳', '👀']
    }
    
    counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    
    for sentiment, emojis in sentiment_emojis.items():
        for emoji in emojis:
            counts[sentiment] += text.count(emoji)
    
    return counts

def hash_text(text: str) -> str:
    """Generate hash of text for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def extract_risk_reward(text: str) -> Optional[Tuple[float, float]]:
    """Extract risk/reward ratio from text."""
    # Look for explicit RR mentions
    rr_match = re.search(r'(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)\s*(?:rr|risk\s*reward)', text.lower())
    if rr_match:
        risk = float(rr_match.group(1))
        reward = float(rr_match.group(2))
        return (risk, reward)
    
    # Look for stop loss and take profit
    sl_match = re.search(r'(?:sl|stop)\s*[:=]?\s*\$?(\d+(?:\.\d+)?)', text.lower())
    tp_match = re.search(r'(?:tp|target|pt)\s*[:=]?\s*\$?(\d+(?:\.\d+)?)', text.lower())
    entry_match = re.search(r'(?:entry|buy|long)\s*[:=@]?\s*\$?(\d+(?:\.\d+)?)', text.lower())
    
    if sl_match and tp_match and entry_match:
        stop = float(sl_match.group(1))
        target = float(tp_match.group(1))
        entry = float(entry_match.group(1))
        
        risk = abs(entry - stop)
        reward = abs(target - entry)
        
        if risk > 0:
            return (1, reward / risk)
    
    return None

def classify_signal_quality(text: str) -> str:
    """Classify signal quality as high/medium/low."""
    score = 0
    
    # Check for specific elements
    if re.search(r'\$[A-Z]{1,6}', text):  # Has ticker
        score += 1
    if re.search(r'\d+(?:\.\d+)?', text):  # Has numbers
        score += 1
    if re.search(r'(?:entry|buy|sell|long|short)', text.lower()):  # Has action
        score += 1
    if re.search(r'(?:tp|target|pt|sl|stop)', text.lower()):  # Has levels
        score += 2
    if re.search(r'(?:\d+%|confidence|conviction)', text.lower()):  # Has confidence
        score += 1
    
    # Length check
    if len(text) > 50:
        score += 1
    
    # Classify
    if score >= 5:
        return 'high'
    elif score >= 3:
        return 'medium'
    else:
        return 'low'