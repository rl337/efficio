"""Educational oil pickup, supply network and crankcase/pan interfaces.

External pump/filter/relief and all seals remain intentionally unspecified.
"""

import math
from dataclasses import dataclass
from typing import List, Optional

from efficio.objects.base import EfficioObject
from efficio.objects.fluids import Point3, TubeNetwork
from efficio.objects.powertrain.engine.resin import ResinHousingGeometry
from efficio.objects.profiles import box, wrap, x_cylinder, y_cylinder
from efficio.objects.shapes import Shape


@dataclass
class LubricationGeometry:
    housing: ResinHousingGeometry
    bore_radius: float = 1.5
    tube_wall: float = 1.0
    pickup_floor_gap: float = 2.0
    gallery_inset: float = 3.0
    external_reach: float = 18.0
    outlet_inset: float = 1.5
    bearing_face_gap: float = 0.2
    gallery_height_offset: float = 2.5
    gallery_end_offset: float = 6.0
    nozzle_below_liner: float = 3.0
    bearing_outlet_x: float = -7.0
    bearing_outlet_z: float = 6.0

    def problems(self) -> List[str]:
        issues = self.housing.problems()
        values = [
            v for k, v in vars(self).items() if k not in ("housing", "bearing_outlet_x")
        ]
        if not all(math.isfinite(v) and v > 0 for v in values) or not math.isfinite(
            self.bearing_outlet_x
        ):
            return issues + [
                "lubrication dimensions must be finite with positive clearances"
            ]
        e = self.housing.engine
        outer = self.bore_radius + self.tube_wall
        if (
            abs(-e.block_half_width + self.gallery_inset) + outer
            >= e.block_half_width + self.housing.clearance
        ):
            issues.append("gallery does not clear the sump wall")
        if (
            self.supply_z <= outer
            or 2 * self.gallery_end_offset >= e.block_length - 2 * e.end_wall
        ):
            issues.append("gallery has no usable clearance")
        if self.nozzle_below_liner <= outer:
            issues.append("outlet body reaches the cylinder liner")
        return issues

    @property
    def bottom(self) -> float:
        return -self.housing.engine.block_half_width - self.housing.pan_drop

    @property
    def service_y(self) -> float:
        e = self.housing.engine
        return (
            (e.cylinder_y(0) + e.cylinder_y(1)) / 2
            if e.cylinders > 1
            else e.cylinder_y(0)
        )

    @property
    def supply_z(self) -> float:
        return self.housing.engine.crank_sweep_radius - self.gallery_height_offset

    @property
    def external_x(self) -> float:
        return -self.housing.engine.block_half_width - self.external_reach

    def pickup_path(self) -> List[Point3]:
        e = self.housing.engine
        x = -e.block_half_width + 2 * self.gallery_inset
        return [
            (
                x,
                self.service_y,
                self.bottom + self.housing.shell + self.pickup_floor_gap,
            ),
            (x, self.service_y, -self.supply_z),
            (self.external_x, self.service_y, -self.supply_z),
        ]

    def supply_paths(self) -> List[List[Point3]]:
        e = self.housing.engine
        x = -e.block_half_width + self.gallery_inset
        z = self.supply_z
        front = e.end_wall + self.gallery_end_offset
        rear = e.block_length - e.end_wall - self.gallery_end_offset
        # Service pressure port joins the longitudinal gallery with a bore overlap.
        paths = [
            [(x, front, z), (x, rear, z)],
            [(self.external_x, self.service_y, z), (x, self.service_y, z)],
        ]
        for i in range(e.cylinders):
            y = e.cylinder_y(i)
            paths.append(
                [
                    (x, y, z),
                    (
                        -e.bore / 2 - self.outlet_inset,
                        y,
                        self.housing.liner_bottom - self.nozzle_below_liner,
                    ),
                ]
            )
        for y, end in [
            (front, e.end_wall + self.bearing_face_gap),
            (rear, e.block_length - e.end_wall - self.bearing_face_gap),
        ]:
            paths.append(
                [
                    (x, y, z),
                    (self.bearing_outlet_x, y, self.bearing_outlet_z),
                    (self.bearing_outlet_x, end, self.bearing_outlet_z),
                ]
            )
        return paths

    def pickup(self) -> TubeNetwork:
        return TubeNetwork([self.pickup_path()], self.bore_radius, self.tube_wall)

    def supply(self) -> TubeNetwork:
        return TubeNetwork(self.supply_paths(), self.bore_radius, self.tube_wall)


class LubricationSump(EfficioObject):
    """Clear candidate pan extended to the liner base; no sealed-joint claim."""

    def __init__(self, geometry: LubricationGeometry):
        self.geometry = geometry

    def shape(self) -> Optional[Shape]:
        g = self.geometry
        if g.problems():
            raise ValueError("Invalid lubrication geometry: " + "; ".join(g.problems()))
        h = g.housing
        e = h.engine
        end = e.end_wall
        length = e.block_length
        inner = e.block_half_width + h.clearance
        outer = inner + h.shell
        pan = box(-outer, outer, end, length - end, g.bottom, h.liner_bottom)
        pan = pan.cut(
            box(
                -inner,
                inner,
                end + h.shell,
                length - end - h.shell,
                g.bottom + h.shell,
                h.liner_bottom + 1,
            )
        )
        # Clearance notches around the existing lower frame rails at both ends.
        # These interfaces require end gaskets/clamps before any liquid trial.
        for sign in (-1, 1):
            x0, x1 = sorted(
                (
                    sign * (e.block_half_width - h.frame_rail - h.clearance),
                    sign * (e.block_half_width + h.clearance),
                )
            )
            pan = pan.cut(
                box(
                    x0,
                    x1,
                    end - 1,
                    length - end + 1,
                    -h.frame_rail - h.clearance,
                    h.clearance,
                )
            )
        # Shaft exits are aligned with the retained end bearings. Seals undecided.
        pan = pan.cut(
            y_cylinder(
                e.crank_journal_diameter / 2 + h.clearance, end - 1, length - end + 1
            )
        )
        # Reuse the drain location from the shallow-pan concept.
        pan = pan.cut(
            x_cylinder(
                h.port_radius,
                -outer - 1,
                -inner + 1,
                end + h.shell + 2 * h.port_radius,
                g.bottom + h.shell + h.port_radius,
            )
        )
        for z in (-g.supply_z, g.supply_z):
            pan = pan.cut(
                x_cylinder(
                    g.bore_radius + g.tube_wall + h.clearance,
                    -outer - 1,
                    -inner + 1,
                    g.service_y,
                    z,
                )
            )
        # Bearing-wetting outlets traverse the two end walls toward the bearing faces.
        pan = pan.cut(
            y_cylinder(
                g.bore_radius + g.tube_wall + h.clearance,
                end - 1,
                length - end + 1,
                g.bearing_outlet_x,
                g.bearing_outlet_z,
            )
        )
        return wrap(pan)
