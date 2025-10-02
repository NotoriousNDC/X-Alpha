"""Signal parsers for different asset classes."""
from .equities import parse_equity
from .crypto import parse_crypto
from .prediction import parse_prediction
from .sports import parse_sports
from .base import ParsedSignal

__all__ = [
    'parse_equity',
    'parse_crypto', 
    'parse_prediction',
    'parse_sports',
    'ParsedSignal'
]