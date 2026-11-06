"""Drivetrain gears: the general gears (``efficio.objects.gears``) fixed to
the drivetrain's gear system. Only drivetrain-specific choices live here."""

from efficio.objects.powertrain.gears.parts import (
    DrivetrainCrownGear,
    DrivetrainSpurGear,
)
from efficio.objects.powertrain.gears.system import (
    DRIVETRAIN_CROWN_ADDENDUM,
    DRIVETRAIN_CROWN_BACKLASH,
    DRIVETRAIN_GEAR_SYSTEM,
)

__all__ = [
    "DRIVETRAIN_CROWN_ADDENDUM",
    "DRIVETRAIN_CROWN_BACKLASH",
    "DRIVETRAIN_GEAR_SYSTEM",
    "DrivetrainCrownGear",
    "DrivetrainSpurGear",
]
