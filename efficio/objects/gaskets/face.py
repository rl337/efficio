"""Explicit planar sealing surfaces and separate gasket artifacts.

Offsets that split, erase or change topology fail closed. The isotropic spread
model preserves volume but does not model rubber mechanics or guarantee sealing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import cast

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.gaskets.geometry import GasketParameters
from efficio.objects.profiles import wrap
from efficio.objects.shapes import Shape


class OpeningRole(Enum):
    WET_CAVITY = "wet_cavity"
    BOLT = "bolt"
    SHAFT = "shaft"
    OTHER = "other_explicit"


@dataclass(frozen=True)
class Opening:
    name: str
    wire: cq.Wire
    role: OpeningRole


@dataclass(frozen=True)
class KeepOut:
    name: str
    solid: cq.Shape


def extrude(face: cq.Face, height: float, normal: cq.Vector) -> cq.Solid:
    return cast(
        cq.Solid,
        cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), normal * height),
    )


def offset(wire: cq.Wire, distance: float) -> cq.Wire:
    if abs(distance) < 1e-10:
        return wire
    edges = wire.Edges()
    if len(edges) == 1 and edges[0].geomType() == "CIRCLE":
        # CQ/OCC offset of a located full-circle wire can apply its Location
        # twice. Reconstruct the exact circle using its world-space center.
        radius = edges[0].radius() + distance
        if radius <= 0:
            raise ValueError("circular opening collapsed")
        return cq.Wire.makeCircle(
            radius, wire.Center(), cq.Face.makeFromWires(wire).normalAt()
        )
    wires = wire.offset2D(distance, kind="intersection")
    if len(wires) != 1 or not wires[0].isValid():
        raise ValueError(
            "boundary offset collapsed or split; explicit redesign required"
        )
    return wires[0]


def footprint(face: cq.Face, outer: float, inner: float) -> cq.Face:
    try:
        result = cq.Face.makeFromWires(
            offset(face.outerWire(), -outer),
            [offset(w, inner) for w in face.innerWires()],
        )
    except Exception as exc:
        raise ValueError("boundary offset failed; explicit redesign required") from exc
    if (
        not result.isValid()
        or len(result.innerWires()) != len(face.innerWires())
        or result.Area() <= 0
    ):
        raise ValueError("offset changed gasket topology")
    return result


class GeneratedGasket(EfficioObject):
    """Separate uncompressed part, placed at the declared face datum."""

    def __init__(self, face: cq.Face, thickness: float, normal: cq.Vector):
        self.face, self.thickness, self.normal = face, thickness, normal

    def shape(self) -> Shape:
        return wrap(
            cq.Workplane("XY").newObject(
                [extrude(self.face, self.thickness, self.normal)]
            )
        )


@dataclass(frozen=True)
class GasketDesign:
    free: GeneratedGasket
    installed_estimate: cq.Solid
    clearance_envelope: cq.Solid
    recess_envelope: cq.Solid
    squeeze_fraction: float
    estimated_spread: float
    gland_fill_fraction: float
    closure_description: str
    minimum_width: float
    limiting_boundaries: str
    stop_planes_checked: bool


@dataclass(frozen=True)
class GasketFace:
    face: cq.Face
    openings: tuple[Opening, ...]
    keepouts: tuple[KeepOut, ...]
    normal: cq.Vector
    closed_height: float
    closure_description: str
    stop_faces: tuple[cq.Face, ...] = ()

    def generate(self, parameters: GasketParameters) -> GasketDesign:
        import math

        errors = parameters.problems()
        if errors:
            raise ValueError(errors[0])
        if self.face.geomType() != "PLANE" or not self.face.isValid():
            raise ValueError("gasket face must be one valid planar face")
        if (
            self.normal.Length == 0
            or abs(
                abs(self.face.normalAt().normalized().dot(self.normal.normalized())) - 1
            )
            > 1e-7
        ):
            raise ValueError("extrusion direction must be normal to the gasket face")
        if (
            not math.isfinite(self.closed_height)
            or self.closed_height <= 0
            or not self.closure_description.strip()
        ):
            raise ValueError("declare positive closed height and hard-stop evidence")
        if parameters.free_thickness <= self.closed_height:
            raise ValueError(
                "free gasket must stand proud of the declared closed height"
            )
        holes = self.face.innerWires()
        if len(holes) != len(self.openings) or any(
            sum(o.wire.isSame(w) for o in self.openings) != 1 for w in holes
        ):
            raise ValueError("every opening must be explicitly identified exactly once")
        if len({o.name for o in self.openings}) != len(self.openings) or any(
            not o.name or not isinstance(o.role, OpeningRole) for o in self.openings
        ):
            raise ValueError("opening names must be unique and roles explicit")
        if len({k.name for k in self.keepouts}) != len(self.keepouts) or any(
            not k.name or not k.solid.isValid() or not k.solid.Solids()
            for k in self.keepouts
        ):
            raise ValueError("keep-outs require unique names and valid volumes")
        normal = self.normal.normalized()
        for stop in self.stop_faces:
            height = (stop.Center() - self.face.Center()).dot(normal)
            if (
                stop.geomType() != "PLANE"
                or not stop.isValid()
                or abs(abs(stop.normalAt().dot(normal)) - 1) > 1e-7
                or abs(height - self.closed_height) > 1e-7
            ):
                raise ValueError("hard-stop face does not match declared closure plane")
        recess = extrude(self.face, self.closed_height, normal)
        flat = footprint(self.face, parameters.outer_inset, parameters.inner_inset)
        from efficio.objects.gaskets.width import measure_band_width

        width, limiting = measure_band_width(flat)
        if width + 1e-7 < parameters.minimum_width:
            raise ValueError(
                f"sealing band {width:.6g} mm at {limiting} is below minimum {parameters.minimum_width:g} mm"
            )
        available = extrude(self.face, parameters.free_thickness, normal)
        free_solid = extrude(flat, parameters.free_thickness, normal)
        if free_solid.cut(available).Volume() > 1e-7 or len(free_solid.Solids()) != 1:
            raise ValueError("inset gasket is not contained by its declared face")
        target_area = flat.Area() * parameters.free_thickness / self.closed_height
        if target_area >= self.face.Area():
            raise ValueError("gasket volume overfills the declared recess")
        # Uniform outward edge motion is only a volume-conserving estimate.
        lo, hi = 0.0, max(parameters.outer_inset, parameters.inner_inset)
        if hi == 0:
            raise ValueError("compression requires lateral room")
        if footprint(flat, -hi, -hi).Area() < target_area:
            raise ValueError("insufficient spread range")
        for _ in range(40):
            mid = (lo + hi) / 2
            if footprint(flat, -mid, -mid).Area() < target_area:
                lo = mid
            else:
                hi = mid
        installed = extrude(footprint(flat, -hi, -hi), self.closed_height, normal)
        guard = extrude(
            footprint(
                flat, -hi * parameters.spread_margin, -hi * parameters.spread_margin
            ),
            self.closed_height,
            normal,
        )
        if guard.cut(recess).Volume() > 1e-7:
            raise ValueError(
                "estimated spread margin escapes recess; redesign gasket/gland"
            )
        for name, solid in (
            ("free", free_solid),
            ("installed", installed),
            ("spread envelope", guard),
            ("recess", recess),
        ):
            if not solid.isValid() or len(solid.Solids()) != 1:
                raise ValueError(f"invalid {name} geometry")
            for keepout in self.keepouts:
                if solid.intersect(keepout.solid).Volume() > 1e-7:
                    raise ValueError(f"{name} intersects keep-out {keepout.name}")
        return GasketDesign(
            GeneratedGasket(flat, parameters.free_thickness, normal),
            installed,
            guard,
            recess,
            1 - self.closed_height / parameters.free_thickness,
            hi,
            free_solid.Volume() / recess.Volume(),
            self.closure_description,
            width,
            limiting,
            bool(self.stop_faces),
        )
