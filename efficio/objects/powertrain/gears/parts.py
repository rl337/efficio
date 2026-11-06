"""Gears fixed to the drivetrain's gear system.

These are :class:`SpurGear` and :class:`CrownGear` with the module, pressure
angle and backlash fixed (``DRIVETRAIN_GEAR_SYSTEM``). Tooth count, width,
bore and hub stay parameters. Pass another ``GearSystem`` to reuse a part
on a different gear train.
"""

from efficio.measures import Measure, Millimeter
from efficio.objects.gears.crown import CrownGear
from efficio.objects.gears.spur import NO_HUB, SpurGear
from efficio.objects.gears.standards import GearSystem
from efficio.objects.powertrain.gears.system import (
    DRIVETRAIN_CROWN_ADDENDUM,
    DRIVETRAIN_CROWN_BACKLASH,
    DRIVETRAIN_GEAR_SYSTEM,
)


class DrivetrainSpurGear(SpurGear):
    """Spur gear on the drivetrain gear system (module 1.5, 25 deg)."""

    def __init__(
        self,
        teeth: int,
        thickness: Measure,
        bore: Measure,
        d_flat: bool = True,
        hub_diameter: Measure = NO_HUB,
        hub_length: Measure = NO_HUB,
        cross_pin_diameter: Measure = NO_HUB,
        cross_pin_length: Measure = NO_HUB,
        system: GearSystem = DRIVETRAIN_GEAR_SYSTEM,
    ):
        self.system = system
        super().__init__(
            system.module,
            teeth,
            thickness,
            bore,
            d_flat,
            system.pressure_angle,
            hub_diameter=hub_diameter,
            hub_length=hub_length,
            backlash=Millimeter(system.backlash),
            cross_pin_diameter=cross_pin_diameter,
            cross_pin_length=cross_pin_length,
        )


class DrivetrainCrownGear(CrownGear):
    """Crown gear on the drivetrain gear system, with the drivetrain's
    crown backlash and shortened addendum as defaults."""

    def __init__(
        self,
        teeth: int,
        pinion_teeth: int,
        body_thickness: Measure,
        bore: Measure,
        d_flat: bool = True,
        backlash: Measure = Millimeter(DRIVETRAIN_CROWN_BACKLASH),
        addendum_coefficient: float = DRIVETRAIN_CROWN_ADDENDUM,
        body_rim: Measure = Millimeter(0.5),
        system: GearSystem = DRIVETRAIN_GEAR_SYSTEM,
    ):
        self.system = system
        super().__init__(
            system.module,
            teeth,
            pinion_teeth,
            body_thickness,
            bore,
            d_flat,
            system.pressure_angle,
            backlash,
            addendum_coefficient,
            body_rim,
        )
