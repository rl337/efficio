"""Deep-groove ball bearing catalogue (pure Python)."""

from dataclasses import dataclass
from enum import Enum
from typing import List

from efficio.objects.powertrain.fits import BEARING_SEAT_CLEARANCE_MM


@dataclass(frozen=True)
class BallBearing:
    designation: str
    bore: float
    outer_diameter: float
    width: float

    @property
    def seat_radius(self) -> float:
        return self.outer_diameter / 2.0 + BEARING_SEAT_CLEARANCE_MM


class StandardBearing(Enum):
    """Common miniature bearings; usable directly as a CLI parameter."""

    B608 = BallBearing("608", 8.0, 22.0, 7.0)
    B625 = BallBearing("625", 5.0, 16.0, 5.0)
    B6800 = BallBearing("6800", 10.0, 19.0, 5.0)
    B6801 = BallBearing("6801", 12.0, 21.0, 5.0)
    B688 = BallBearing("688", 8.0, 16.0, 5.0)

    @property
    def spec(self) -> BallBearing:
        value: BallBearing = self.value
        return value

    @staticmethod
    def examples() -> List[str]:
        return ["B608", "B625", "B6800"]


BEARING_608 = StandardBearing.B608.spec
BEARING_625 = StandardBearing.B625.spec
BEARING_6800 = StandardBearing.B6800.spec
