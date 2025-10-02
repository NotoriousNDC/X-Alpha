from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class ParsedSignal:
    asset_class: str
    instrument: Optional[str]
    market_ref: Optional[str]
    side: str
    team: Optional[str] = None
    line_type: Optional[str] = None
    line: Optional[float] = None
    odds_price: Optional[float] = None
    size: Optional[float] = None
    confidence: Optional[float] = None
    horizon_seconds: Optional[int] = None
    expiry_time: Optional[str] = None
    extracted: Optional[Dict[str, Any]] = None

    def to_row(self) -> Dict[str, Any]:
        row = asdict(self)
        row['extracted'] = row.get('extracted') or {}
        return row
