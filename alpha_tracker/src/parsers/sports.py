"""Sports betting signal parser."""
import re
from typing import List, Optional, Tuple
from .base import ParsedSignal

# Common team patterns
TEAM_PATTERNS = {
    'NFL': ['chiefs', 'bills', '49ers', 'eagles', 'cowboys', 'ravens', 'bengals', 'dolphins'],
    'NBA': ['lakers', 'celtics', 'heat', 'warriors', 'bucks', 'nuggets', 'suns', '76ers'],
    'MLB': ['yankees', 'dodgers', 'astros', 'braves', 'rays', 'orioles', 'rangers'],
    'NHL': ['avalanche', 'oilers', 'panthers', 'rangers', 'stars', 'bruins'],
}

def detect_league(text: str) -> Optional[str]:
    """Detect sports league from text."""
    text_lower = text.lower()
    
    # Direct league mentions
    if 'nfl' in text_lower or 'football' in text_lower:
        return 'NFL'
    elif 'nba' in text_lower or 'basketball' in text_lower:
        return 'NBA'
    elif 'mlb' in text_lower or 'baseball' in text_lower:
        return 'MLB'
    elif 'nhl' in text_lower or 'hockey' in text_lower:
        return 'NHL'
    
    # Check team mentions
    for league, teams in TEAM_PATTERNS.items():
        if any(team in text_lower for team in teams):
            return league
    
    return None

def extract_bet_type(text: str) -> Tuple[Optional[str], Optional[float]]:
    """Extract bet type and line value."""
    text_lower = text.lower()
    
    # Spread patterns
    spread_match = re.search(r'([\+\-]\d+(?:\.\d)?)', text)
    if spread_match:
        return 'spread', float(spread_match.group(1))
    
    # Total patterns
    total_patterns = [
        r'[oO](\d+(?:\.\d)?)',
        r'[uU](\d+(?:\.\d)?)',
        r'(?:over|under)\s+(\d+(?:\.\d)?)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return 'total', float(match.group(1))
    
    # Moneyline
    if any(term in text_lower for term in ['ml', 'moneyline', 'money line']):
        return 'moneyline', None
    
    return None, None

def extract_odds(text: str) -> Optional[float]:
    """Extract American odds."""
    match = re.search(r'([\+\-]\d{3,4})', text)
    if match:
        return float(match.group(1))
    return None

def extract_team(text: str) -> Optional[str]:
    """Extract team reference."""
    text_lower = text.lower()
    
    # Try to find team abbreviations
    abbrev_match = re.search(r'\b([A-Z]{2,4})\b', text)
    if abbrev_match:
        return abbrev_match.group(1)
    
    # Check known teams
    for league_teams in TEAM_PATTERNS.values():
        for team in league_teams:
            if team in text_lower:
                return team.upper()[:3]
    
    return None

def extract_units(text: str) -> Optional[float]:
    """Extract bet size in units."""
    patterns = [
        r'(\d+(?:\.\d)?)\s*units?',
        r'(\d+(?:\.\d)?)\s*u\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    # Check for confidence indicators
    text_lower = text.lower()
    if 'max' in text_lower or 'hammer' in text_lower:
        return 5.0
    elif 'strong' in text_lower or 'love' in text_lower:
        return 3.0
    elif 'lean' in text_lower or 'small' in text_lower:
        return 1.0
    
    return None

def parse_sports(text: str) -> List[ParsedSignal]:
    """Parse sports betting signals."""
    signals = []
    
    league = detect_league(text)
    if not league:
        return signals
    
    bet_type, line = extract_bet_type(text)
    if not bet_type:
        return signals
    
    team = extract_team(text)
    odds = extract_odds(text)
    units = extract_units(text)
    
    # Determine side
    if bet_type == 'total':
        side = 'over' if 'over' in text.lower() or 'o' in text[:3].lower() else 'under'
    else:
        side = 'favorite' if line and line < 0 else 'underdog'
    
    # Calculate confidence
    confidence = 0.5
    if units:
        if units >= 3:
            confidence = 0.8
        elif units >= 2:
            confidence = 0.65
        elif units <= 1:
            confidence = 0.4
    
    signal = ParsedSignal(
        asset_class='sports',
        instrument=f"{league}:{team}" if team else league,
        market_ref=None,
        side=side,
        team=team,
        line_type=bet_type,
        line=line,
        odds_price=odds,
        size=units,
        confidence=confidence,
        extracted={
            'league': league,
            'raw_text': text[:500]
        }
    )
    
    signals.append(signal)
    return signals

