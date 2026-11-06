"""Gear standards: tooth size (module or diametral pitch), pressure angle,
and ``GearSystem``, the values every gear in a mesh must share."""

from dataclasses import dataclass
from enum import Enum
from typing import List


class GearStandard(Enum):

    def pitch_radius(self, num_teeth: int) -> float:
        """
        Compute the pitch radius based on whether the gear is metric (module) or imperial (DP).
        - For metric gears: R_p = (m * N) / 2
        - For diametral pitch gears: R_p = (N / (2 * DP))
        """
        if isinstance(self, MetricModule):
            return float(self.value * num_teeth) / 2
        elif isinstance(self, DiametralPitch):
            return float(num_teeth / (2 * self.value))
        else:
            raise ValueError("Invalid gear standard type")

    def addendum_radius(self, num_teeth: int) -> float:
        pitch_radius = self.pitch_radius(num_teeth)
        if isinstance(self, MetricModule):
            return float(pitch_radius + self.value)
        elif isinstance(self, DiametralPitch):
            return float(pitch_radius + 1 / self.value)
        else:
            raise ValueError("Invalid gear standard type")


# 📏 **Metric (ISO) Gear Modules**
class MetricModule(GearStandard):
    MODULE_0_8 = 0.8
    MODULE_1 = 1.0
    MODULE_1_25 = 1.25
    MODULE_1_5 = 1.5
    MODULE_2 = 2.0
    MODULE_2_5 = 2.5
    MODULE_3 = 3.0
    MODULE_4 = 4.0

    # Aliases for 3D printing
    MODULE_FINE = MODULE_1
    MODULE_NORMAL = MODULE_1_5
    MODULE_LARGE = MODULE_2

    @staticmethod
    def examples() -> List[str]:
        return [
            "MODULE_FINE",
            "MODULE_NORMAL",
            "MODULE_LARGE",
            "MODULE_1",
            "MODULE_1_5",
            "MODULE_2",
        ]


# ⚙️ **Imperial (AGMA) Diametral Pitch (DP)**
class DiametralPitch(GearStandard):
    PITCH_24 = 24
    PITCH_20 = 20
    PITCH_16 = 16
    PITCH_14 = 14
    PITCH_12 = 12
    PITCH_10 = 10

    # Aliases for 3D printing
    PITCH_FINE = PITCH_20
    PITCH_NORMAL = PITCH_16
    PITCH_LARGE = PITCH_12

    @staticmethod
    def examples() -> List[str]:
        return [
            "PITCH_FINE",
            "PITCH_NORMAL",
            "PITCH_LARGE",
            "PITCH_20",
            "PITCH_16",
            "PITCH_12",
        ]


class PressureAngle(Enum):
    """
    Pressure angle is the angle between the line of action and the line normal to the gear surface.
    """

    MODERN = 20
    OLD = 14.5
    HIGH_TORQUE = 25

    @staticmethod
    def examples() -> List[str]:
        return ["MODERN", "OLD", "HIGH_TORQUE"]


@dataclass(frozen=True)
class GearSystem:
    """Values that every gear in one mesh must share.

    Gears mesh only if module and pressure angle match. Backlash is the
    tangential play each gear removes from its tooth thickness.
    """

    module: MetricModule
    pressure_angle: PressureAngle
    backlash: float = 0.15
