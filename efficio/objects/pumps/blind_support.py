"""Rounded wet end with blind journals; seal seat is an interface, not a seal."""

import math
from typing import Optional, cast

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.connectors import HoseBarb, HoseBarbDimensions
from efficio.objects.fits import cross_pin_offset
from efficio.objects.gaskets import GasketFace, KeepOut, Opening, OpeningRole
from efficio.objects.gaskets.face import extrude, footprint
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
        gasket_style: str = "capsule",
        full_face_land: float = 0.3,
    ):
        if kind not in {"body", "cover", "gasket", "driver_shaft", "idler_shaft"}:
            raise ValueError("unknown blind-support part")
        if gasket_style not in {"capsule", "full_face"}:
            raise ValueError("unknown gasket style")
        if not math.isfinite(full_face_land) or full_face_land <= 0:
            raise ValueError("full-face hard land must be positive")
        if gasket_style == "full_face" and kind == "gasket":
            raise ValueError("use generate_gasket for the full-face free part")
        self.gasket_style, self.full_face_land = gasket_style, full_face_land
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

    def gasket_faces(self) -> dict[str, GasketFace]:
        if self.kind != "body":
            return {}
        shape = self.shape()
        assert shape is not None
        solid = cast(cq.Shape, shape.workplane().val())
        g, d = self.d.pump, self.d
        z = g.depth - d.gasket_depth
        faces = [
            f
            for f in solid.Faces()
            if f.geomType() == "PLANE"
            and abs(f.Center().z - z) < 1e-7
            and abs(f.normalAt().z) > 0.999999
        ]
        if len(faces) != 1:
            raise ValueError(
                "pump gasket recess face is ambiguous; explicit remapping required"
            )
        face = faces[0]
        openings = []
        for wire in face.innerWires():
            center = wire.Center()
            if abs(center.x - g.centres / 2) < 1e-6 and abs(center.y) < 1e-6:
                openings.append(
                    Opening("enclosed_wet_region", wire, OpeningRole.WET_CAVITY)
                )
            else:
                matches = [
                    i
                    for i, (x, y) in enumerate(d.bolt_points)
                    if abs(center.x - x) < 1e-6 and abs(center.y - y) < 1e-6
                ]
                if len(matches) != 1:
                    raise ValueError("unrecognized pump gasket opening")
                openings.append(Opening(f"bolt_{matches[0]}", wire, OpeningRole.BOLT))
        expected = {"enclosed_wet_region"}
        if self.gasket_style == "full_face":
            expected |= {f"bolt_{i}" for i in range(4)}
        if {o.name for o in openings} != expected:
            raise ValueError("pump gasket opening set changed")
        wet = GearPumpGeometry(**vars(g)).cavity()
        swept = cylinder(
            g.tip_radius, g.base + g.face_clearance, g.depth - g.face_clearance
        ).fuse(
            cylinder(
                g.tip_radius,
                g.base + g.face_clearance,
                g.depth - g.face_clearance,
                x=g.centres,
            )
        )
        return {
            "cover_seal": GasketFace(
                face,
                tuple(openings),
                (
                    KeepOut("wet cavity", wet),
                    KeepOut("full rotor swept volumes", swept),
                ),
                cq.Vector(0, 0, 1),
                d.gasket_depth,
                "Existing flat body/cover lands close at z=%.6g; no new stops generated"
                % g.depth,
                tuple(
                    f
                    for f in solid.Faces()
                    if f.geomType() == "PLANE"
                    and abs(f.Center().z - g.depth) < 1e-7
                    and abs(f.normalAt().z) > 0.999999
                ),
            )
        }

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
            solid = solid.cut(g.cavity())
            if self.gasket_style == "capsule":
                solid = solid.cut(gasket)
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
            root = root.cut(g.cavity())
            if self.gasket_style == "capsule":
                root = root.cut(gasket)
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
        if self.kind == "body" and self.gasket_style == "full_face":
            tops = [
                f
                for f in solid.Faces()
                if f.geomType() == "PLANE"
                and abs(f.Center().z - g.depth) < 1e-7
                and abs(f.normalAt().z) > 0.999999
            ]
            if len(tops) != 1:
                raise ValueError("full mating face is ambiguous")
            floor = footprint(
                tops[0], self.full_face_land, self.full_face_land, "arc"
            ).translate((0, 0, -d.gasket_depth))
            solid = solid.cut(extrude(floor, d.gasket_depth, cq.Vector(0, 0, 1)))
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
