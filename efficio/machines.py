"""Fabrication machine catalogue (pure Python).

Build volumes come from the manufacturers' published specifications.  The
Makera Z1's 4th axis is described by the cylinder it can machine, stored as
(length, diameter, diameter).
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from efficio.measures import Measure, Millimeter


@dataclass(frozen=True)
class BuildVolume:
    x: Measure
    y: Measure
    z: Measure

    def fits(self, dimensions: Tuple[float, float, float]) -> bool:
        """True if a part of these dimensions fits in any orientation."""
        limits = sorted((self.x.value(), self.y.value(), self.z.value()))
        candidate = sorted(dimensions)
        return all(size <= limit for size, limit in zip(candidate, limits))


class MachineKind(Enum):
    FDM_PRINTER = "fdm_printer"
    CNC_MILL = "cnc_mill"
    CNC_ROTARY = "cnc_rotary"


@dataclass(frozen=True)
class MachineProfile:
    name: str
    build_volume: BuildVolume
    kind: MachineKind = MachineKind.FDM_PRINTER


# Older code and tests call printer profiles by this name.
PrinterProfile = MachineProfile


class StandardMachine(Enum):
    PRUSA_MK4 = MachineProfile(
        "Original Prusa MK4",
        BuildVolume(Millimeter(250), Millimeter(210), Millimeter(220)),
    )
    MAKERA_Z1 = MachineProfile(
        "Makera Z1 (3-axis)",
        BuildVolume(Millimeter(200), Millimeter(200), Millimeter(100)),
        MachineKind.CNC_MILL,
    )
    MAKERA_Z1_4TH_AXIS = MachineProfile(
        "Makera Z1 4th axis",
        BuildVolume(Millimeter(150), Millimeter(80), Millimeter(80)),
        MachineKind.CNC_ROTARY,
    )

    @property
    def spec(self) -> MachineProfile:
        value: MachineProfile = self.value
        return value

    @staticmethod
    def examples() -> List[str]:
        return [m.name for m in StandardMachine]


PRUSA_MK4 = StandardMachine.PRUSA_MK4.spec
MAKERA_Z1 = StandardMachine.MAKERA_Z1.spec
