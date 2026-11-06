"""General gear types, usable by any project.

- ``standards``: tooth-size standards (``MetricModule``, ``DiametralPitch``),
  ``PressureAngle``, and ``GearSystem``, the values every gear in a mesh must
  share.
- ``base``: abstract rotary drivers (``AbstractCogwheel`` and friends).
- ``involute`` / ``face``: pure involute and face-gear geometry, no CadQuery.
- ``spur``: involute ``SpurGear`` and ``CompoundSpurGear``.
- ``crown``: ``CrownGear``, a face gear meshing a spur pinion at 90 degrees.
- ``simple``: rectangular, trapezoidal and spherical gears sized from an outer
  radius (molds, decoration); not standard-meshing.

Gears fixed to one project's gear system go in that project's package, for
example ``efficio.objects.powertrain.gears``.
"""

from efficio.objects.gears.base import (
    AbstractCogwheel,
    AbstractPulley,
    AbstractRotaryDriver,
    AbstractSprocket,
)
from efficio.objects.gears.crown import CrownGear
from efficio.objects.gears.face import FaceGearGeometry, crown_mesh_phase
from efficio.objects.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    involute_function,
    mesh_phase,
)
from efficio.objects.gears.markings import (
    GearArcMarking,
    GearFaceMarker,
    GearMarkingStyle,
    standard_involute_markings,
)
from efficio.objects.gears.simple import (
    AbstractGear,
    AbstractGearTooth,
    AbstractSphericalGearTooth,
    AbstractTrapezoidalGearTooth,
    GearToothType,
    RectangularGear,
    SphericalGear,
    TrapezoidalGear,
    TrapezoidalSphericalGearTooth,
)
from efficio.objects.gears.spur import (
    DEFAULT_BACKLASH,
    NO_HUB,
    CompoundSpurGear,
    SpurGear,
    bore_allowance,
)
from efficio.objects.gears.standards import (
    DiametralPitch,
    GearStandard,
    GearSystem,
    MetricModule,
    PressureAngle,
)

__all__ = [
    "AbstractCogwheel",
    "AbstractGear",
    "AbstractGearTooth",
    "AbstractPulley",
    "AbstractRotaryDriver",
    "AbstractSphericalGearTooth",
    "AbstractSprocket",
    "AbstractTrapezoidalGearTooth",
    "CompoundSpurGear",
    "CrownGear",
    "DEFAULT_BACKLASH",
    "DiametralPitch",
    "FaceGearGeometry",
    "GearArcMarking",
    "GearFaceMarker",
    "GearMarkingStyle",
    "GearStandard",
    "GearSystem",
    "GearToothType",
    "InvoluteGearGeometry",
    "MetricModule",
    "NO_HUB",
    "PressureAngle",
    "RectangularGear",
    "SphericalGear",
    "SpurGear",
    "TrapezoidalGear",
    "TrapezoidalSphericalGearTooth",
    "bore_allowance",
    "centre_distance",
    "crown_mesh_phase",
    "involute_function",
    "mesh_phase",
    "standard_involute_markings",
]
