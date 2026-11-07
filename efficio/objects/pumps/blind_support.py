"""Rounded wet end with blind journals; seal seat is an interface, not a seal."""

import math
from typing import Optional, cast

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.connectors import HoseBarb, HoseBarbDimensions
from efficio.objects.fits import cross_pin_offset
from efficio.objects.profiles import wrap, x_cylinder
from efficio.objects.pumps.external_gear import GearPumpGeometry
from efficio.objects.pumps.geometry import BlindSupportDimensions
from efficio.objects.shapes import Shape


def cylinder(
    radius: float, z0: float, z1: float, x: float = 0, y: float = 0
) -> cq.Shape:
    return cq.Solid.makeCylinder(radius, z1 - z0, cq.Vector(x, y, z0))


def capsule(centres: float, radius: float, z0: float, z1: float) -> cq.Shape:
    middle = cq.Solid.makeBox(centres, 2 * radius, z1 - z0, cq.Vector(0, -radius, z0))
    return (
        cylinder(radius, z0, z1)
        .fuse(cylinder(radius, z0, z1, x=centres), middle)
        .clean()
    )


def beveled_cylinder(
    radius: float,
    z0: float,
    z1: float,
    bevel: float,
    bottom: bool,
    x: float = 0,
    y: float = 0,
) -> cq.Shape:
    """45-degree exposed-end rim; build before union to avoid cusp chamfer failures."""
    if bevel == 0:
        return cylinder(radius, z0, z1, x, y)
    low, high = (z0 + bevel, z1) if bottom else (z0, z1 - bevel)
    cone = cq.Solid.makeCone(
        radius - bevel if bottom else radius,
        radius if bottom else radius - bevel,
        bevel,
        cq.Vector(x, y, z0 if bottom else z1 - bevel),
    )
    return cylinder(radius, low, high, x, y).fuse(cone).clean()


class BlindSupportPart(EfficioObject):
    """Body, cover, compressed gasket envelope or pinned ground-rod shaft.

    Gasket geometry represents installed thickness. No elastomer deformation,
    seal lip, purchased bush or mechanical coupling is silently simulated.
    """

    def __init__(
        self,
        dimensions: BlindSupportDimensions,
        kind: str,
        terminal: Optional[HoseBarbDimensions] = None,
        terminal_start: float = 0.0,
        root_cover_clearance: float = 0.05,
    ):
        if kind not in {"body", "cover", "gasket", "driver_shaft", "idler_shaft"}:
            raise ValueError("unknown blind-support part")
        self.d, self.kind = dimensions, kind
        self.terminal, self.terminal_start = terminal, terminal_start
        self.root_cover_clearance = root_cover_clearance
        if not math.isfinite(root_cover_clearance) or root_cover_clearance <= 0:
            raise ValueError("root cover clearance must be positive and finite")
        if terminal is not None and (
            not math.isfinite(terminal_start)
            or terminal_start <= 0
            or terminal.bore_radius != dimensions.pump.port_radius
        ):
            raise ValueError(
                "terminal requires positive placement and a matching pump bore"
            )

    def shape(self) -> Optional[Shape]:
        d = self.d
        g = GearPumpGeometry(**vars(d.pump))
        top = g.depth + g.cover
        if self.kind.endswith("shaft"):
            end = (
                top + g.shaft_extension
                if self.kind == "driver_shaft"
                else top - d.front_web - d.end_gap
            )
            solid = cylinder(d.shaft_radius, d.back_web + d.end_gap, end)
            pin_z = g.base + g.face_clearance + cross_pin_offset(g.rotor_pin_diameter)
            solid = solid.cut(
                cast(
                    cq.Shape,
                    x_cylinder(
                        g.rotor_pin_diameter / 2,
                        -g.shaft_diameter,
                        g.shaft_diameter,
                        z=pin_z,
                    ).val(),
                )
            )
            return wrap(cq.Workplane("XY").newObject([solid]))
        inside = g.radius + d.gasket_inset
        gasket = capsule(
            g.centres, inside + d.gasket_width, g.depth - d.gasket_depth, g.depth
        ).cut(
            capsule(g.centres, inside, g.depth - d.gasket_depth - 0.01, g.depth + 0.01)
        )
        if self.kind == "gasket":
            return wrap(cq.Workplane("XY").newObject([gasket]))
        z0, z1 = (0.0, g.depth) if self.kind == "body" else (g.depth, top)
        if d.exterior_offset:
            bottom = self.kind == "body"
            solid = (
                beveled_cylinder(g.radius + d.exterior_offset, z0, z1, d.bevel, bottom)
                .fuse(
                    beveled_cylinder(
                        g.radius + d.exterior_offset,
                        z0,
                        z1,
                        d.bevel,
                        bottom,
                        x=g.centres,
                    ),
                    *(
                        beveled_cylinder(
                            d.boss_radius, z0, z1, d.bevel, bottom, x=x, y=y
                        )
                        for x, y in d.bolt_points
                    ),
                )
                .clean()
            )
        else:
            solid = capsule(g.centres, g.half_height, z0, z1)
        roots: list[cq.Shape] = []
        if self.kind == "body" and self.terminal is not None:
            terminal = HoseBarb(self.terminal)
            for sign in (-1, 1):
                solid = solid.fuse(self.place_terminal(terminal.barbed_stem(), sign))
                root = terminal.root_envelope()
                if root is not None:
                    # Relieve only the added flare above the body's joint plane;
                    # preserve original stem/barbs and removable cover/gasket.
                    placed = self.place_terminal(root, sign)
                    bounds = placed.BoundingBox()
                    keep = cq.Solid.makeBox(
                        bounds.xlen + 2,
                        bounds.ylen + 2,
                        g.depth - self.root_cover_clearance - bounds.zmin + 1,
                        cq.Vector(bounds.xmin - 1, bounds.ymin - 1, bounds.zmin - 1),
                    )
                    roots.append(placed.intersect(keep))
        if self.kind == "body":
            if self.terminal is None:
                solid = solid.cut(g.port_void(-1)).cut(g.port_void(1))
            solid = solid.cut(g.cavity()).cut(gasket)
            for x in (0.0, g.centres):
                solid = solid.cut(
                    cylinder(
                        g.shaft_diameter / 2 + g.journal_clearance,
                        d.back_web,
                        g.base + 0.01,
                        x=x,
                    )
                )
        else:
            solid = solid.cut(
                cylinder(
                    g.shaft_diameter / 2 + g.journal_clearance, z0 - 0.01, z1 + 0.01
                )
            )
            solid = solid.cut(
                cylinder(
                    g.shaft_diameter / 2 + g.journal_clearance,
                    z0 - 0.01,
                    z1 - d.front_web,
                    x=g.centres,
                )
            )
            solid = solid.cut(cylinder(d.seal_radius, top - d.seal_depth, top + 0.01))
        for x, y in d.bolt_points:
            solid = solid.cut(cylinder(g.bolt_radius, z0 - 0.01, z1 + 0.01, x=x, y=y))
        for root in roots:
            # Add the relieved support to the already machined base body, keeping
            # its existing faces intact. Cut every functional void from support.
            root = root.cut(g.cavity()).cut(gasket)
            assert self.terminal is not None
            for x in (0.0, g.centres):
                root = root.cut(
                    cylinder(
                        g.shaft_diameter / 2 + g.journal_clearance,
                        d.back_web,
                        g.base + 0.01,
                        x=x,
                    )
                )
            for x, y in d.bolt_points:
                root = root.cut(cylinder(g.bolt_radius, z0 - 0.01, z1 + 0.01, x=x, y=y))
            solid = solid.fuse(root)
        if self.kind == "body" and self.terminal is not None:
            # One canonical drilling avoids coincident cylindrical seam faces
            # from overlapping side and terminal cutters during support fusion.
            reach = self.terminal_start + self.terminal.length + 0.01
            drilling = cq.Solid.makeCylinder(
                g.port_radius,
                2 * reach,
                cq.Vector(g.centres / 2, -reach, g.port(1)[2]),
                cq.Vector(0, 1, 0),
            )
            solid = solid.cut(drilling)
        return wrap(cq.Workplane("XY").newObject([solid.clean()]))

    def place_terminal(self, shape: cq.Shape, sign: int) -> cq.Shape:
        if sign not in (-1, 1):
            raise ValueError("port sign must be -1 or +1")
        g = self.d.pump
        return shape.rotate((0, 0, 0), (1, 0, 0), -90 * sign).translate(
            (g.centres / 2, sign * self.terminal_start, g.port(sign)[2])
        )


def measured_housing_interfaces(d: BlindSupportDimensions) -> dict[str, float]:
    """Exact BRep wire distances at selected critical sections, in mm.

    This is not a global minimum-wall search: ports/openings, 3D junction
    stresses, permeability, tolerances and surface defects need other checks.
    """
    parts: dict[str, cq.Shape] = {}
    for kind in ("body", "cover", "gasket"):
        result = BlindSupportPart(d, kind).shape()
        assert result is not None
        value = result.workplane().val()
        assert isinstance(value, cq.Shape)
        parts[kind] = value

    def outer(solid: cq.Shape, side: str) -> cq.Wire:
        faces = cq.Workplane("XY").newObject([solid]).faces(side).vals()
        wires = [f.outerWire() for f in faces if isinstance(f, cq.Face)]
        return max(wires, key=lambda w: w.BoundingBox().xlen)

    measured = {
        "gasket_outer_waist_vertical": outer(parts["body"], ">Z").distance(
            outer(parts["gasket"], ">Z")
        )
    }
    distances = []
    for kind, side, z in (
        ("body", "<Z", 0.0),
        ("cover", ">Z", d.pump.depth + d.pump.cover),
    ):
        rim = outer(parts[kind], side)
        for x, y in d.bolt_points:
            hole = cq.Wire.makeCircle(
                d.pump.bolt_radius, cq.Vector(x, y, z), cq.Vector(0, 0, 1)
            )
            distances.append(rim.distance(hole))
    measured["bolt_boss_ligament"] = min(distances)
    return measured
