from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import json


class EventType(str, Enum):
    USER_REGISTERED = "user.registered"
    USER_LOGGED_IN = "user.logged_in"
    BOT_STARTED = "bot.started"
    BOT_STOPPED = "bot.stopped"
    BOT_STATE_UPDATE = "bot.state_update"
    TRADE_EXECUTED = "trade.executed"
    TRADE_SIMULATED = "trade.simulated"
    RISK_DAILY_LIMIT = "risk.daily_limit"
    RISK_TRADE_LIMIT = "risk.trade_limit"
    SIGNAL_ALIGNED = "signal.aligned"
    SYSTEM_STARTUP = "system.startup"


@dataclass
class Event:
    type: EventType
    user_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    source: str = "system"

    def to_dict(self):
        return {"id": self.id, "type": self.type.value, "user_id": self.user_id, "data": self.data, "timestamp": self.timestamp, "source": self.source}

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d):
        return cls(type=EventType(d["type"]), user_id=d.get("user_id"), data=d.get("data", {}), id=d.get("id", ""), timestamp=d.get("timestamp", 0), source=d.get("source", "system"))
