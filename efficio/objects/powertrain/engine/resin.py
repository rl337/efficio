"""Separate educational engine housing parts, with undecided seals and process.

Clear resin is a material intent, not an optical or casting feasibility claim.
All parts use engine-local coordinates; liners are centered on local Y = 0.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.engine.block import CylinderHead, EngineBlockHalf
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.profiles import box, cylinder, wrap, x_cylinder
from efficio.objects.shapes import Shape


class ResinHousingPart(Enum):
    LINER = "liner"
    DECK = "deck"
    HEAD = "head"
    JACKET = "jacket"
    FRONT_SUPPORT = "front_support"
    REAR_SUPPORT = "rear_support"
    BEARING_FRAME = "bearing_frame"
    OIL_PAN = "oil_pan"


@dataclass
class ResinHousingGeometry:
    engine: EngineGeometry
    liner_wall: float = 3.0
    shell: float = 2.5
    clearance: float = 0.2
    deck_thickness: float = 4.0
    flange_width: float = 1.5
    flange_height: float = 2.0
    frame_rail: float = 4.0
    pan_drop: float = 5.0
    port_radius: float = 2.0

    @property
    def liner_radius(self) -> float:
        return self.engine.bore / 2 + self.liner_wall

    @property
    def liner_bottom(self) -> float:
        return self.engine.crankcase_relief_height

    @property
    def jacket_top(self) -> float:
        return self.engine.deck_height - self.deck_thickness

    def problems(self) -> List[str]:
        import math

        e = self.engine
        issues = e.problems()
        if e.windowed_block:
            issues.append("resin assembly requires continuous, unwindowed cylinders")
        if not all(
            math.isfinite(v) and v > 0
            for v in (
                self.liner_wall,
                self.shell,
                self.clearance,
                self.deck_thickness,
                self.flange_width,
                self.flange_height,
                self.frame_rail,
                self.pan_drop,
                self.port_radius,
            )
        ):
            return issues + ["housing dimensions must be positive and finite"]
        if (
            2 * (self.liner_radius + self.flange_width + self.clearance)
            >= e.cylinder_spacing
        ):
            issues.append("liner flange seats overlap")
        if self.liner_radius + self.clearance >= e.block_half_width - self.shell:
            issues.append("no coolant gap beside liners")
        if self.flange_height + self.clearance >= self.deck_thickness:
            issues.append("liner flange needs a deck shoulder")
        if self.liner_bottom + self.shell >= self.jacket_top:
            issues.append("coolant cavity has no height")
        skirt_at_bdc = (
            e.rod_length
            - e.crank_throw
            - (e.piston_height - e.piston_compression_height)
        )
        if skirt_at_bdc < self.liner_bottom:
            issues.append("piston skirt exits the continuous liner at BDC")
        if self.frame_rail >= e.block_half_width:
            issues.append("bearing frame rail consumes crank clearance")
        if (
            self.liner_bottom + 2 * self.shell + 3 * self.port_radius >= self.jacket_top
            or -e.block_half_width - self.pan_drop + self.shell + 2 * self.port_radius
            >= -self.frame_rail
        ):
            issues.append("side ports do not fit within the cavity walls")
        return issues


class ResinEngineHousingPart(EfficioObject):
    """Parameterized candidate casting/assembly part, without mold tooling."""

    def __init__(self, geometry: ResinHousingGeometry, part: ResinHousingPart):
        self.geometry = geometry
        self.part = part

    def shape(self) -> Optional[Shape]:
        g = self.geometry
        errors = g.problems()
        if errors:
            raise ValueError("Invalid resin housing: " + "; ".join(errors))
        e = g.engine
        hw, length, end, deck = (
            e.block_half_width,
            e.block_length,
            e.end_wall,
            e.deck_height,
        )
        r, fit = g.liner_radius, g.clearance
        if self.part is ResinHousingPart.LINER:
            liner = cylinder(r, g.liner_bottom, deck)
            liner = liner.union(
                cylinder(r + g.flange_width, deck - g.flange_height, deck)
            )
            return wrap(liner.cut(cylinder(e.bore / 2, g.liner_bottom - 1, deck + 1)))
        if self.part is ResinHousingPart.HEAD:
            head = CylinderHead(e).shape()
            assert head is not None
            return wrap(head.workplane().translate((0, 0, deck)))
        if self.part is ResinHousingPart.DECK:
            part = box(-hw, hw, 0, length, g.jacket_top, deck)
            for i in range(e.cylinders):
                y = e.cylinder_y(i)
                part = part.cut(cylinder(r + fit, g.jacket_top - 1, deck + 1, 0, y))
                part = part.cut(
                    cylinder(
                        r + g.flange_width + fit,
                        deck - g.flange_height - fit,
                        deck + 1,
                        0,
                        y,
                    )
                )
            for x, y in e.head_bolt_positions():
                part = part.cut(
                    cylinder(
                        e.fastener.spec.clearance_radius,
                        g.jacket_top - 1,
                        deck + 1,
                        x,
                        y,
                    )
                )
            return wrap(part)
        if self.part is ResinHousingPart.JACKET:
            part = box(-hw, hw, end, length - end, g.liner_bottom, g.jacket_top)
            part = part.cut(
                box(
                    -hw + g.shell,
                    hw - g.shell,
                    end + g.shell,
                    length - end - g.shell,
                    g.liner_bottom + g.shell,
                    g.jacket_top + 1,
                )
            )
            for i in range(e.cylinders):
                part = part.cut(
                    cylinder(
                        r + fit,
                        g.liner_bottom - 1,
                        g.jacket_top + 1,
                        0,
                        e.cylinder_y(i),
                    )
                )
            # Two actual bores through one side; no fittings/seals are implied.
            for y, z in (
                (
                    end + g.shell + g.port_radius + 1,
                    g.liner_bottom + g.shell + 2 * g.port_radius,
                ),
                (
                    length - end - g.shell - g.port_radius - 1,
                    g.jacket_top - g.shell - 2 * g.port_radius,
                ),
            ):
                part = part.cut(
                    x_cylinder(g.port_radius, -hw - 1, -hw + g.shell + 1, y, z)
                )
            return wrap(part)
        if self.part in (ResinHousingPart.FRONT_SUPPORT, ResinHousingPart.REAR_SUPPORT):
            original = EngineBlockHalf(e, True).shape()
            assert original is not None
            y0, y1 = (
                (0, end)
                if self.part is ResinHousingPart.FRONT_SUPPORT
                else (length - end, length)
            )
            return wrap(
                original.workplane().intersect(
                    box(-hw - 1, hw + 1, y0, y1, 0, g.jacket_top)
                )
            )
        if self.part is ResinHousingPart.BEARING_FRAME:
            original = EngineBlockHalf(e, False).shape()
            assert original is not None
            keep = box(-hw - 1, hw + 1, 0, end, -hw - 1, 0)
            keep = keep.union(box(-hw - 1, hw + 1, length - end, length, -hw - 1, 0))
            for sign in (-1, 1):
                x0, x1 = sorted((sign * (hw - g.frame_rail), sign * (hw + 1)))
                keep = keep.union(box(x0, x1, 0, length, -g.frame_rail, 0))
            return wrap(original.workplane().intersect(keep))
        bottom = -hw - g.pan_drop
        pan = box(-hw, hw, end, length - end, bottom, -g.frame_rail)
        pan = pan.cut(
            box(
                -hw + g.shell,
                hw - g.shell,
                end + g.shell,
                length - end - g.shell,
                bottom + g.shell,
                1,
            )
        )
        pan = pan.cut(
            x_cylinder(
                g.port_radius,
                -hw - 1,
                -hw + g.shell + 1,
                end + g.shell + 2 * g.port_radius,
                bottom + g.shell + g.port_radius,
            )
        )
        return wrap(pan)
