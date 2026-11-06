"""The drivetrain's gear system (pure data, no CadQuery).

Every mesh in the transaxle (crank pinion and crown, gearbox stages,
differential) uses module 1.5 with a 25 degree pressure angle. 25 degrees
gives thicker tooth roots than the common 20 degrees and avoids undercut on
the 12-tooth pinions.
"""

from efficio.objects.gears.standards import GearSystem, MetricModule, PressureAngle

DRIVETRAIN_GEAR_SYSTEM = GearSystem(
    module=MetricModule.MODULE_1_5,
    pressure_angle=PressureAngle.HIGH_TORQUE,
    backlash=0.15,
)

# The crown mesh needs more play than the spur meshes: at 0.15 mm the
# interference check found the crown and pinion grazing.
DRIVETRAIN_CROWN_BACKLASH = 0.3
# A shortened crown addendum keeps the tips from coming to a point too soon
# toward the outer edge, which leaves enough face width for 48 teeth at 25 deg.
DRIVETRAIN_CROWN_ADDENDUM = 0.8
