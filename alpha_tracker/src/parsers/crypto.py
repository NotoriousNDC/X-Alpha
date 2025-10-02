"""Enhanced crypto signal parser with improved pattern recognition."""
import re
from typing import List, Optional, Tuple
from .base import ParsedSignal

# Major crypto symbols and their variations
CRYPTO_SYMBOLS = {
    'BTC': ['bitcoin', 'btc'],
    'ETH': ['ethereum', 'eth', 'ether'],
    'BNB': ['binance', 'bnb'],
    'SOL': ['solana', 'sol'],
    'XRP': ['ripple', 'xrp'],
    'ADA': ['cardano', 'ada'],
    'AVAX': ['avalanche', 'avax'],
    'DOGE': ['dogecoin', 'doge'],
    'DOT': ['polkadot', 'dot'],
    'MATIC': ['polygon', 'matic'],
    'LINK': ['chainlink', 'link'],
    'UNI': ['uniswap', 'uni'],
    'ATOM': ['cosmos', 'atom'],
    'ARB': ['arbitrum', 'arb'],
    'OP': ['optimism', 'op'],
    'INJ': ['injective', 'inj'],
    'TIA': ['celestia', 'tia'],
    'SEI': ['sei'],
    'PEPE': ['pepe'],
    'WLD': ['worldcoin', 'wld'],
    'BLUR': ['blur'],
    'FET': ['fetch', 'fet'],
    'RNDR': ['render', 'rndr'],
    'NEAR': ['near'],
    'APT': ['aptos', 'apt'],
    'SUI': ['sui'],
    'USDT': ['tether', 'usdt'],
    'USDC': ['usdc', 'usd coin'],
}

# Create reverse mapping for quick lookups
CRYPTO_NAME_MAP = {}
for symbol, names in CRYPTO_SYMBOLS.items():
    for name in names:
        CRYPTO_NAME_MAP[name.lower()] = symbol

# Patterns for crypto extraction
CRYPTO_PATTERN = r'\$([A-Z]{2,6})\b'
CRYPTO_CONTEXT_PATTERN = r'\b(bitcoin|ethereum|btc|eth|sol|bnb|ada|avax|doge|matic|link|uni|atom|arb|op)\b'

# Leverage and position patterns
LEVERAGE_PATTERN = r'(\d+(?:\.\d+)?)[xX]\s*(?:leverage|lev)'
PERP_PATTERN = r'\b(perp|perpetual|futures?|spot)\b'

# DeFi specific patterns
DEFI_PATTERNS = [
    r'(?:stake|staking|yield|farm|farming|lp|liquidity)',
    r'(?:airdrop|ido|ico|presale)',
    r'(?:bridge|swap|dex)',
]

# Chain specific patterns
CHAIN_PATTERNS = {
    'ethereum': ['eth', 'erc20', 'mainnet'],
    'binance': ['bsc', 'bnb chain', 'bep20'],
    'solana': ['sol', 'spl'],
    'polygon': ['matic', 'polygon'],
    'arbitrum': ['arb', 'arbitrum'],
    'optimism': ['op', 'optimism'],
    'base': ['base'],
    'avalanche': ['avax', 'avalanche'],
}

def normalize_crypto_symbol(text: str) -> Optional[str]:
    """Normalize crypto mentions to standard symbols."""
    text_lower = text.lower()
    
    # Check for direct symbol match with $
    dollar_match = re.search(CRYPTO_PATTERN, text, re.IGNORECASE)
    if dollar_match:
        symbol = dollar_match.group(1).upper()
        # Verify it's a known crypto
        if symbol in CRYPTO_SYMBOLS or len(symbol) <= 5:
            return symbol
    
    # Check for name mentions
    for name, symbol in CRYPTO_NAME_MAP.items():
        if name in text_lower:
            return symbol
    
    # Check for any uppercase sequence that might be a ticker
    matches = re.findall(r'\b([A-Z]{2,6})\b', text)
    for match in matches:
        if match in CRYPTO_SYMBOLS:
            return match
        # Common newer tokens
        if len(match) <= 5 and match not in {'THE', 'AND', 'FOR', 'USD', 'USDT', 'USDC'}:
            return match
    
    return None

def extract_trading_type(text: str) -> str:
    """Determine if it's spot, futures, or perp trading."""
    text_lower = text.lower()
    
    if re.search(r'\b(perp|perpetual)\b', text_lower):
        return 'perpetual'
    elif re.search(r'\bfutures?\b', text_lower):
        return 'futures'
    elif re.search(r'\bspot\b', text_lower):
        return 'spot'
    elif re.search(LEVERAGE_PATTERN, text_lower):
        return 'perpetual'  # Leverage implies derivatives
    
    return 'spot'  # Default

def extract_leverage(text: str) -> Optional[float]:
    """Extract leverage amount."""
    match = re.search(LEVERAGE_PATTERN, text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Check for isolated/cross margin mentions
    if re.search(r'\b(?:isolated|cross)\s*margin\b', text.lower()):
        return 2.0  # Conservative default for margin
    
    return None

def extract_entry_exit_targets(text: str) -> dict:
    """Extract entry, take profit, and stop loss levels."""
    info = {}
    
    # Entry patterns
    entry_patterns = [
        r'(?:entry|buy|long|short)\s*(?:at|@|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
        r'(?:bought|entered|longed|shorted)\s*(?:at|@)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
        r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:entry|buy)',
    ]
    
    for pattern in entry_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                info['entry'] = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    # Take profit patterns (multiple TPs possible)
    tp_patterns = [
        r'(?:tp|take\s*profit|target|pt)(?:\s*\d+)?\s*(?:at|@|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
        r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:target|tp)',
    ]
    
    take_profits = []
    for pattern in tp_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                tp = float(match.group(1).replace(',', ''))
                if tp not in take_profits:
                    take_profits.append(tp)
            except:
                pass
    
    if take_profits:
        info['take_profits'] = sorted(take_profits)
        info['target'] = take_profits[0]  # First TP as primary target
    
    # Stop loss patterns
    sl_patterns = [
        r'(?:sl|stop\s*loss|stop)\s*(?:at|@|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
        r'(?:risk|risking)\s*(?:to|at)\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
        r'(?:invalidation)\s*(?:at|@|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
    ]
    
    for pattern in sl_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                info['stop_loss'] = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    return info

def extract_position_size(text: str) -> Optional[float]:
    """Extract position size in USD or percentage."""
    text_lower = text.lower()
    
    # Percentage of portfolio
    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s+)?(?:portfolio|account|capital|allocation)', text_lower)
    if pct_match:
        return float(pct_match.group(1)) / 100
    
    # Dollar amounts
    dollar_patterns = [
        r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kmb])?(?:\s+|$)',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(usd|usdt|usdc|busd)',
    ]
    
    for pattern in dollar_patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = float(match.group(1).replace(',', ''))
            multiplier = match.group(2) if len(match.groups()) > 1 else None
            if multiplier:
                if multiplier.lower() == 'k':
                    amount *= 1000
                elif multiplier.lower() == 'm':
                    amount *= 1000000
                elif multiplier.lower() == 'b':
                    amount *= 1000000000
            return amount
    
    return None

def extract_confidence_timeframe(text: str) -> Tuple[Optional[float], Optional[int]]:
    """Extract confidence and timeframe."""
    confidence = None
    timeframe = None
    
    text_lower = text.lower()
    
    # Confidence patterns
    conf_patterns = [
        (r'(\d+)\s*%\s*(?:confidence|conviction|certain|sure)', lambda m: float(m.group(1))/100),
        (r'(?:very\s+)?(?:high|strong|bullish)\s+(?:confidence|conviction)?', lambda m: 0.85),
        (r'(?:medium|moderate|neutral)', lambda m: 0.60),
        (r'(?:low|weak|bearish)\s+(?:confidence|conviction)?', lambda m: 0.35),
        (r'(?:moon|ape|yolo|all\s*in)', lambda m: 0.95),  # Crypto culture
        (r'(?:dca|accumulate|nibble)', lambda m: 0.50),
    ]
    
    for pattern, extractor in conf_patterns:
        match = re.search(pattern, text_lower)
        if match:
            confidence = extractor(match)
            break
    
    # Timeframe patterns (in seconds)
    time_patterns = [
        (r'(?:scalp|1m|5m|15m)', 900),  # 15 minutes
        (r'(?:intraday|day\s*trade|today)', 86400),  # 1 day
        (r'(?:swing|weekly?|1w)', 604800),  # 1 week
        (r'(?:monthly?|30d|1m)', 2592000),  # 30 days
        (r'(?:quarterly?|90d|3m)', 7776000),  # 90 days
        (r'(?:long\s*term|yearly?|hodl)', 31536000),  # 1 year
    ]
    
    for pattern, seconds in time_patterns:
        if re.search(pattern, text_lower):
            timeframe = seconds
            break
    
    return confidence, timeframe

def extract_side(text: str) -> str:
    """Determine if long or short."""
    text_lower = text.lower()
    
    long_score = 0
    short_score = 0
    
    # Long indicators
    long_patterns = ['long', 'buy', 'bought', 'bullish', 'moon', 'pump', 'accumulate', 'hodl', 'bid']
    for pattern in long_patterns:
        if pattern in text_lower:
            long_score += 1
    
    # Short indicators
    short_patterns = ['short', 'sell', 'sold', 'bearish', 'dump', 'fade', 'puts', 'hedge']
    for pattern in short_patterns:
        if pattern in text_lower:
            short_score += 1
    
    # Emoji sentiment (crypto culture)
    if '🚀' in text or '🌙' in text or '📈' in text or '💚' in text or '🟢' in text:
        long_score += 1
    if '📉' in text or '🔴' in text or '🩸' in text or '💔' in text:
        short_score += 1
    
    return 'short' if short_score > long_score else 'long'

def parse_crypto(text: str) -> List[ParsedSignal]:
    """Parse crypto trading signals from text."""
    signals = []
    
    # Extract primary crypto symbol
    symbol = normalize_crypto_symbol(text)
    if not symbol:
        return signals
    
    # Normalize to trading pair
    instrument = f"{symbol}-USD" if symbol not in ['USDT', 'USDC', 'BUSD', 'DAI'] else symbol
    
    # Extract trading parameters
    trading_type = extract_trading_type(text)
    leverage = extract_leverage(text)
    side = extract_side(text)
    levels = extract_entry_exit_targets(text)
    size = extract_position_size(text)
    confidence, timeframe = extract_confidence_timeframe(text)
    
    # Build the signal
    signal = ParsedSignal(
        asset_class='crypto',
        instrument=instrument,
        market_ref=None,
        side=side,
        confidence=confidence,
        horizon_seconds=timeframe,
        size=size,
        extracted={
            'trading_type': trading_type,
            'leverage': leverage,
            'entry': levels.get('entry'),
            'target': levels.get('target'),
            'take_profits': levels.get('take_profits', []),
            'stop_loss': levels.get('stop_loss'),
            'raw_text': text[:500]
        }
    )
    
    signals.append(signal)
    
    # Check for multiple crypto mentions
    all_symbols = re.findall(CRYPTO_PATTERN, text)
    mentioned_cryptos = set()
    for match in all_symbols:
        mentioned_cryptos.add(match.upper())
    
    # Also check for named mentions
    for name, sym in CRYPTO_NAME_MAP.items():
        if name in text.lower():
            mentioned_cryptos.add(sym)
    
    # Add additional signals for other mentioned cryptos
    for other_symbol in mentioned_cryptos:
        if other_symbol != symbol and other_symbol not in ['USDT', 'USDC', 'USD']:
            other_instrument = f"{other_symbol}-USD"
            signals.append(ParsedSignal(
            asset_class='crypto',
                instrument=other_instrument,
            market_ref=None,
                side=side,
                confidence=confidence,
                horizon_seconds=timeframe,
                extracted={'trading_type': trading_type, 'raw_text': text[:500]}
            ))
    
    return signals