"""2.5D bearing plate whose outline hugs its features."""

from typing import List, Optional, Sequence

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.planar import Point, hull_of_circles
from efficio.objects.powertrain.gearbox.features import PlateHole, PlateSeat
from efficio.objects.profiles import bearing_seat_cutter, cylinder, prism, wrap
from efficio.objects.shapes import Shape


class BearingPlate(EfficioObject):
    """Flat plate: convex outline around bearing seats and holes.

    Seats are pocketed from the inner face (local z = 0).  Any set of shafts
    and fasteners works, so the same class makes gearbox side plates, motor
    mounts or bearing carriers.
    """

    def __init__(
        self,
        thickness: Measure,
        seats: Sequence[PlateSeat],
        holes: Sequence[PlateHole],
    ):
        if not seats and not holes:
            raise ValueError("BearingPlate needs at least one feature")
        self.thickness = thickness
        self.seats = list(seats)
        self.holes = list(holes)

    def outline(self) -> List[Point]:
        circles = [(s.centre, s.outline_radius) for s in self.seats]
        circles += [(h.centre, h.outline_radius) for h in self.holes]
        return hull_of_circles(circles)

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        plate = prism(self.outline(), 0.0, t)
        for seat in self.seats:
            x, y = seat.centre
            plate = plate.cut(
                bearing_seat_cutter(seat.bearing, t, seat.through_radius, x, y)
            )
        for hole in self.holes:
            x, y = hole.centre
            plate = plate.cut(cylinder(hole.radius, -1.0, t + 1.0, x, y))
        return wrap(plate)
