"""Fasteners: metric thread catalogue, bolts, nuts and bolt channels.

Generic classes take a :class:`MetricThread`; ``M3...`` classes fix only the
thread.  Concrete sizes (an M3 x 10 bolt) belong where they are used.
"""

from efficio.objects.fasteners.bolts import (
    DEFAULT_CHANNEL_PADDING,
    DEFAULT_FASTENER_CLEARANCE,
    Bolt,
    BoltAssembly,
    BoltChannel,
    BoltHead,
    BoltShaft,
    HexNut,
    M3Bolt,
    M3BoltAssembly,
    M3BoltChannel,
    M3BoltHead,
    M3BoltShaft,
    M3HexNut,
)
from efficio.objects.fasteners.threads import MetricThread, ThreadSpec

__all__ = [
    "DEFAULT_CHANNEL_PADDING",
    "DEFAULT_FASTENER_CLEARANCE",
    "Bolt",
    "BoltAssembly",
    "BoltChannel",
    "BoltHead",
    "BoltShaft",
    "HexNut",
    "M3Bolt",
    "M3BoltAssembly",
    "M3BoltChannel",
    "M3BoltHead",
    "M3BoltShaft",
    "M3HexNut",
    "MetricThread",
    "ThreadSpec",
]
