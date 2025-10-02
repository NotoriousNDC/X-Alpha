"""Enhanced prediction market signal parser."""
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from .base import ParsedSignal

# Platform patterns
PLATFORM_PATTERNS = {
    'polymarket': [
        r'polymarket\.com/event/([a-zA-Z0-9\-]+)',
        r'polymarket\.com/market/([a-zA-Z0-9\-]+)',
        r'poly\.market/([a-zA-Z0-9\-]+)',
        r'pm:([a-zA-Z0-9\-]+)',
    ],
    'manifold': [
        r'manifold\.markets/([a-zA-Z0-9\-_]+)/([a-zA-Z0-9\-_]+)',
        r'manifold\.markets/embed/([a-zA-Z0-9\-_]+)',
        r'mm:([a-zA-Z0-9\-_]+)',
    ],
    'metaculus': [
        r'metaculus\.com/questions/(\d+)',
        r'metaculus:(\d+)',
    ],
    'kalshi': [
        r'kalshi\.com/markets/([a-zA-Z0-9\-]+)',
        r'kalshi:([a-zA-Z0-9\-]+)',
    ],
    'predictit': [
        r'predictit\.org/markets/detail/(\d+)',
        r'predictit:(\d+)',
    ]
}

# Side/position patterns
POSITION_PATTERNS = {
    'yes': ['yes', 'buy yes', 'long yes', 'agree', 'will happen', 'bullish', 'support', 'for'],
    'no': ['no', 'buy no', 'long no', 'disagree', 'won\'t happen', 'bearish', 'against', 'fade']
}

# Probability/confidence patterns
PROB_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability|likely|odds|prob)',
    r'(?:probability|chance|likely|odds|prob)\s*(?:is|at|of)?\s*(\d+(?:\.\d+)?)\s*%',
    r'(?:i\s+(?:think|believe|estimate))\s*(\d+(?:\.\d+)?)\s*%',
    r'(?:market\s+(?:is|at))\s*(\d+(?:\.\d+)?)\s*%',
    r'(?:currently|now|trading)\s*(?:at)?\s*(\d+(?:\.\d+)?)[c¢]',  # cents notation
]

# Size patterns specific to prediction markets
PM_SIZE_PATTERNS = [
    r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:on|in|position|bet)',
    r'(\d+(?:,\d{3})*)\s*(?:shares?|contracts?)',
    r'(?:bet|wager|position)\s*(?:of|size)?\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
]

# Resolution timeline patterns
RESOLUTION_PATTERNS = [
    (r'(?:resolves?|settles?|closes?)\s+today', 86400),
    (r'(?:resolves?|settles?|closes?)\s+(?:this\s+)?week', 604800),
    (r'(?:resolves?|settles?|closes?)\s+(?:this\s+)?month', 2592000),
    (r'(?:resolves?|settles?|closes?)\s+(?:by|before|on)\s+(\w+)', None),  # Date parsing needed
    (r'(?:election|debate|event)\s+(?:day|night)', 86400),
    (r'(?:earnings|report|announcement)', 259200),  # ~3 days
]

# Market category patterns
CATEGORY_PATTERNS = {
    'politics': ['election', 'president', 'congress', 'senate', 'governor', 'vote', 'poll', 'democrat', 'republican', 'gop', 'biden', 'trump'],
    'economics': ['gdp', 'inflation', 'cpi', 'unemployment', 'fed', 'rate', 'recession', 'jobs', 'fomc'],
    'crypto': ['bitcoin', 'ethereum', 'btc', 'eth', 'crypto', 'defi', 'nft'],
    'sports': ['nfl', 'nba', 'mlb', 'nhl', 'soccer', 'football', 'basketball', 'baseball', 'championship', 'playoffs', 'super bowl'],
    'tech': ['ai', 'gpt', 'chatgpt', 'google', 'apple', 'microsoft', 'tesla', 'ipo', 'launch'],
    'weather': ['hurricane', 'temperature', 'rain', 'snow', 'storm', 'climate'],
    'entertainment': ['oscar', 'emmy', 'movie', 'box office', 'album', 'spotify'],
}

def extract_market_ref(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract market reference and platform."""
    # Check each platform's patterns
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if platform == 'manifold' and len(match.groups()) > 1:
                    # Manifold has user/market format
                    return f"{match.group(1)}/{match.group(2)}", platform
                else:
                    return match.group(1), platform
    
    # Try to extract any URL
    url_pattern = r'https?://[^\s]+'
    url_match = re.search(url_pattern, text)
    if url_match:
        url = url_match.group(0)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'polymarket' in domain:
            return parsed.path.split('/')[-1], 'polymarket'
        elif 'manifold' in domain:
            parts = parsed.path.split('/')
            if len(parts) >= 3:
                return f"{parts[-2]}/{parts[-1]}", 'manifold'
        elif 'metaculus' in domain:
            return parsed.path.split('/')[-1], 'metaculus'
        elif 'kalshi' in domain:
            return parsed.path.split('/')[-1], 'kalshi'
    
    return None, None

def extract_position(text: str) -> Optional[str]:
    """Determine YES or NO position."""
    text_lower = text.lower()
    
    yes_score = 0
    no_score = 0
    
    for yes_term in POSITION_PATTERNS['yes']:
        if yes_term in text_lower:
            yes_score += 1
            # Boost for explicit market language
            if yes_term in ['buy yes', 'long yes']:
                yes_score += 2
    
    for no_term in POSITION_PATTERNS['no']:
        if no_term in text_lower:
            no_score += 1
            # Boost for explicit market language
            if no_term in ['buy no', 'long no']:
                no_score += 2
    
    # Check for percentage with context
    prob_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if prob_match:
        prob = float(prob_match.group(1))
        if prob > 60:
            yes_score += 1
        elif prob < 40:
            no_score += 1
    
    # Check for emoji sentiment
    if '✅' in text or '👍' in text or '🟢' in text:
        yes_score += 1
    if '❌' in text or '👎' in text or '🔴' in text:
        no_score += 1
    
    if yes_score > no_score:
        return 'yes'
    elif no_score > yes_score:
        return 'no'
    
    return None

def extract_probability(text: str) -> Optional[float]:
    """Extract stated probability."""
    for pattern in PROB_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            prob = float(match.group(1))
            # Handle cents notation
            if pattern.endswith('[c¢]'):
                return prob / 100
            # Handle percentage
            return prob / 100 if prob > 1 else prob
    
    # Check for qualitative assessments
    text_lower = text.lower()
    qualitative = {
        'very likely': 0.80,
        'likely': 0.70,
        'probable': 0.65,
        'toss up': 0.50,
        'coin flip': 0.50,
        'unlikely': 0.30,
        'very unlikely': 0.20,
        'long shot': 0.15,
        'no chance': 0.05,
    }
    
    for phrase, prob in qualitative.items():
        if phrase in text_lower:
            return prob
    
    return None

def extract_size_contracts(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract position size and number of contracts."""
    size = None
    contracts = None
    
    for pattern in PM_SIZE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(',', '')
            if 'share' in pattern or 'contract' in pattern:
                contracts = float(value)
            else:
                size = float(value)
            
            if size or contracts:
                break
    
    # If we have contracts but no size, estimate size
    if contracts and not size:
        # Assume average price of 50 cents per contract
        size = contracts * 0.50
    
    return size, contracts

def extract_resolution_time(text: str) -> Optional[int]:
    """Extract expected resolution timeframe in seconds."""
    text_lower = text.lower()
    
    for pattern, seconds in RESOLUTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            if seconds:
                return seconds
            # TODO: Parse specific dates if needed
    
    # Check for specific event mentions
    if 'election' in text_lower:
        if '2024' in text:
            return 31536000  # ~1 year
        elif 'primary' in text_lower:
            return 7776000  # ~3 months
    
    return None

def detect_category(text: str) -> Optional[str]:
    """Detect market category from context."""
    text_lower = text.lower()
    
    category_scores = {}
    for category, keywords in CATEGORY_PATTERNS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    return None

def parse_prediction(text: str) -> List[ParsedSignal]:
    """Parse prediction market signals from text."""
    signals = []
    
    # Extract market reference
    market_ref, platform = extract_market_ref(text)
    if not market_ref:
        # No explicit market link, check if there's enough context
        if not any(word in text.lower() for word in ['polymarket', 'manifold', 'metaculus', 'kalshi', 'prediction', 'bet', 'odds']):
            return signals
        # Create a synthetic market ref from text
        market_ref = f"inferred_{hash(text[:100]) % 1000000}"
    
    # Extract position
    side = extract_position(text)
    if not side:
        # Try to infer from probability
        prob = extract_probability(text)
        if prob:
            side = 'yes' if prob > 0.5 else 'no'
        else:
            return signals  # Can't determine position
    
    # Extract other parameters
    probability = extract_probability(text)
    size, contracts = extract_size_contracts(text)
    resolution_time = extract_resolution_time(text)
    category = detect_category(text)
    
    # Calculate confidence based on stated probability vs market action
    confidence = None
    if probability:
        if side == 'yes':
            confidence = probability
        else:
            confidence = 1 - probability
    
    # Create the signal
    signal = ParsedSignal(
        asset_class='prediction',
        instrument=None,
        market_ref=market_ref,
        side=side,
        confidence=confidence,
        horizon_seconds=resolution_time,
        size=size,
        extracted={
            'platform': platform,
            'probability': probability,
            'contracts': contracts,
            'category': category,
            'raw_text': text[:500]
        }
    )
    
    signals.append(signal)
    
    # Check for multiple market references
    all_refs = []
    for platform_patterns in PLATFORM_PATTERNS.values():
        for pattern in platform_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ref = match.group(1) if len(match.groups()) == 1 else f"{match.group(1)}/{match.group(2)}"
                if ref not in all_refs and ref != market_ref:
                    all_refs.append(ref)
    
    # Add signals for other markets mentioned
    for other_ref in all_refs:
        signals.append(ParsedSignal(
            asset_class='prediction',
            instrument=None,
            market_ref=other_ref,
            side=side,
            confidence=confidence,
            extracted={'raw_text': text[:500]}
        ))
    
    return signals