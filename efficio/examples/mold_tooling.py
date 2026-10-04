from efficio.measures import Inch, Millimeter
from efficio.objects.gears import SphericalGear
from efficio.objects.mold_tooling import MoldPolarity, MoldTooling, PRUSA_MK4
from efficio.objects.vases import TriangularFlaskVase


def resin_spherical_gear_tooling() -> MoldTooling:
    """Two-inch spherical gear -> negative silicone mold -> resin cast."""
    gear = SphericalGear(radius=Inch(1), tooth_count=16)
    return MoldTooling(
        master=gear,
        polarity=MoldPolarity.NEGATIVE,
        silicone_thickness=Millimeter(8),
        cottle_wall=Millimeter(4),
        printer=PRUSA_MK4,
    )


def plaster_triangular_flask_tooling() -> MoldTooling:
    """Positive silicone intermediate for a plaster mold workflow."""
    vase = TriangularFlaskVase(
        width=Millimeter(80),
        height=Millimeter(140),
        depth=Millimeter(45),
        neck=Millimeter(24),
    )
    return MoldTooling(
        master=vase,
        polarity=MoldPolarity.POSITIVE,
        silicone_thickness=Millimeter(10),
        cottle_wall=Millimeter(4),
        printer=PRUSA_MK4,
    )
