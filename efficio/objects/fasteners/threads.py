"""Metric fastener catalogue (pure Python).

Dimensions per size:
* thread pitch: ISO 261 coarse;
* socket head cap screw head diameter and height: ISO 4762;
* hex nut width across flats and height: ISO 4032;
* clearance hole: ISO 273 medium series;
* tap drill: 100 % coarse-thread tap drill.

Nut widths across corners are the width across flats divided by cos 30 deg,
rounded to 0.01 mm.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


@dataclass(frozen=True)
class ThreadSpec:
    designation: str
    major_diameter: float
    pitch: float
    head_diameter: float
    head_height: float
    nut_across_flats: float
    nut_across_corners: float
    nut_height: float
    clearance_hole: float
    tap_drill: float

    @property
    def radius(self) -> float:
        return self.major_diameter / 2.0

    @property
    def head_radius(self) -> float:
        return self.head_diameter / 2.0

    @property
    def clearance_radius(self) -> float:
        return self.clearance_hole / 2.0

    @property
    def tap_radius(self) -> float:
        return self.tap_drill / 2.0

    def pocket_depth(self, clearance: float = 0.2) -> float:
        """Depth of a pocket that hides either a head or a nut."""
        return max(self.head_height, self.nut_height) + clearance

    def pocket_across_corners(self, clearance: float = 0.3) -> float:
        """Hex pocket that takes a nut (and therefore also a head that is no
        wider than the nut's flats)."""
        return self.nut_across_corners + clearance


class MetricThread(Enum):
    """Standard metric sizes; usable directly as a CLI parameter."""

    M2 = ThreadSpec("M2", 2.0, 0.4, 3.8, 2.0, 4.0, 4.62, 1.6, 2.4, 1.6)
    M2_5 = ThreadSpec("M2.5", 2.5, 0.45, 4.5, 2.5, 5.0, 5.77, 2.0, 2.9, 2.05)
    M3 = ThreadSpec("M3", 3.0, 0.5, 5.5, 3.0, 5.5, 6.35, 2.4, 3.4, 2.5)
    M4 = ThreadSpec("M4", 4.0, 0.7, 7.0, 4.0, 7.0, 8.08, 3.2, 4.5, 3.3)
    M5 = ThreadSpec("M5", 5.0, 0.8, 8.5, 5.0, 8.0, 9.24, 4.7, 5.5, 4.2)
    M6 = ThreadSpec("M6", 6.0, 1.0, 10.0, 6.0, 10.0, 11.55, 5.2, 6.6, 5.0)

    @property
    def spec(self) -> ThreadSpec:
        value: ThreadSpec = self.value
        return value

    @staticmethod
    def examples() -> List[str]:
        return ["M2", "M3", "M4", "M5"]
