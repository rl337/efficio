"""Stylized stacking-chess pieces built from :mod:`.geometry` dimensions.

Every piece shares a bevelled base, a platform with a rounded top, a concave
stem and (except the rook) a rounded shoulder; the head is what tells them
apart.  Heads that are flat slabs (knight head, king cross) lie in the XZ
plane, so XZ is the natural parting plane for a two-part mold.
"""

import math
from typing import List, Optional, Sequence

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.games.chess.geometry import (
    BishopDimensions,
    ChessBodyDimensions,
    KingDimensions,
    KnightDimensions,
    PawnDimensions,
    Point,
    QueenDimensions,
    RookDimensions,
)
from efficio.objects.profiles import cylinder, wrap
from efficio.objects.shapes import Shape


def _revolve_profile(
    start: Point,
    lines: Sequence[Point] = (),
    spline: Sequence[Point] = (),
    closing: Sequence[Point] = (),
) -> cq.Workplane:
    """Revolve a closed (radius, z) profile about Z.

    From ``start`` the profile runs straight through ``lines``, then as one
    spline through ``spline``, then straight through ``closing`` and back.
    """
    wp = cq.Workplane("XZ").moveTo(*start)
    for point in lines:
        wp = wp.lineTo(*point)
    if spline:
        wp = wp.spline(list(spline), includeCurrent=True)
    for point in closing:
        wp = wp.lineTo(*point)
    return wp.close().revolve(360, (0, 0, 0), (0, 1, 0))


def _bevel_above(solid: cq.Workplane, z_min: float, size: float) -> cq.Workplane:
    """Chamfer every edge whose centre is above ``z_min`` (not the seat)."""
    reach = 1000.0
    selector = cq.selectors.BoxSelector(  # type: ignore[no-untyped-call]
        (-reach, -reach, z_min), (reach, reach, reach)
    )
    return solid.edges(selector).chamfer(size)


class AbstractStylizedChessPiece(EfficioObject):
    """Shared body; subclasses add the head."""

    def __init__(self, body: ChessBodyDimensions):
        self.body = body

    # -- what a subclass provides -------------------------------------------
    def stem_top_radius(self) -> float:
        raise NotImplementedError

    def shoulder_z(self) -> float:
        return self.body.back_row_shoulder_z

    def shoulder_radius(self) -> Optional[float]:
        """``None`` when the head itself sits on the stem (the rook)."""
        raise NotImplementedError

    def head(self) -> cq.Workplane:
        raise NotImplementedError

    def dimension_problems(self) -> List[str]:
        raise NotImplementedError

    # -- shared --------------------------------------------------------------
    def problems(self) -> List[str]:
        return self.body.problems() + self.dimension_problems()

    def _check(self) -> None:
        problems = self.problems()
        if problems:
            raise ValueError("; ".join(problems))

    def shoulder_top(self) -> float:
        return self.shoulder_z() + self.body.shoulder_height

    def body_solid(self) -> cq.Workplane:
        b = self.body
        base = (
            cylinder(b.base_radius, 0, b.base_height)
            .faces(">Z")
            .edges()
            .chamfer(b.base_top_chamfer)
            .faces("<Z")
            .edges()
            .chamfer(b.base_bottom_chamfer)
        )
        platform = (
            cylinder(b.platform_radius, b.base_height, b.platform_top)
            .faces(">Z")
            .edges()
            .fillet(b.edge_round)
        )
        stem_points = b.stem_profile(self.stem_top_radius(), self.shoulder_z())
        stem = _revolve_profile(
            (0, stem_points[0][1]),
            lines=stem_points[:1],
            spline=stem_points[1:],
            closing=[(0, self.shoulder_z() + b.stem_overlap)],
        )
        solid = base.union(platform).union(stem)
        radius = self.shoulder_radius()
        if radius is not None:
            shoulder = (
                cylinder(radius, self.shoulder_z(), self.shoulder_top())
                .edges()
                .fillet(b.edge_round)
            )
            solid = solid.union(shoulder)
        return solid

    def solid(self) -> cq.Workplane:
        solid = self.body_solid().union(self.head())
        if self.body.pin_socket_depth > 0:
            socket = cylinder(
                self.body.pin_socket_diameter / 2, 0, self.body.pin_socket_depth
            )
            solid = solid.cut(socket)
        return solid

    def shape(self) -> Optional[Shape]:
        return wrap(self.solid())


class StylizedPawn(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: PawnDimensions = PawnDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_z(self) -> float:
        return self.body.pawn_shoulder_z

    def shoulder_radius(self) -> Optional[float]:
        return self.dimensions.shoulder_radius

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z = self.shoulder_top() + d.ball_center_above_shoulder()
        return cq.Workplane().sphere(d.ball_radius).translate((0, 0, z))


class StylizedRook(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: RookDimensions = RookDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_radius(self) -> Optional[float]:
        return None

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z = self.shoulder_z()
        head = (
            cq.Workplane()
            .box(
                d.head_width, d.head_width, d.head_height, centered=(True, True, False)
            )
            .translate((0, 0, z))
        )
        floor = z + d.head_height - d.crenel_depth
        through, tall = 2 * d.head_width, 2 * d.crenel_depth
        slots = [(d.crenel_width, through)]
        if d.cross_crenels:
            slots.append((through, d.crenel_width))
        for sx, sy in slots:
            cutter = (
                cq.Workplane()
                .box(sx, sy, tall, centered=(True, True, False))
                .translate((0, 0, floor))
            )
            head = head.cut(cutter)
        return head


class StylizedKnight(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: KnightDimensions = KnightDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_radius(self) -> Optional[float]:
        return self.dimensions.shoulder_radius

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z0 = self.shoulder_top()
        outline = [(x, z0 + z) for x, z in d.head_outline]
        head = (
            cq.Workplane("XZ")
            .polyline(outline)
            .close()
            .extrude(d.head_thickness / 2, both=True)
        )
        head = _bevel_above(head, z0 + self.body.bevel_clearance, d.bevel)
        ex, ez = d.eye_center[0], z0 + d.eye_center[1]
        eye = (
            cq.Workplane("XZ")
            .center(ex, ez)
            .circle(d.eye_diameter / 2)
            .extrude(d.head_thickness, both=True)
        )
        span = 4 * self.body.base_radius
        keep = (
            cq.Workplane()
            .box(span, d.head_thickness - 2 * d.eye_depth, span)
            .translate((0, 0, ez))
        )
        return head.cut(eye.cut(keep))


class StylizedBishop(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: BishopDimensions = BishopDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_radius(self) -> Optional[float]:
        return self.dimensions.shoulder_radius

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z0 = self.shoulder_top()
        profile = [(r, z0 + z) for r, z in d.head_profile()]
        head = _revolve_profile((0, z0), lines=profile[:1], spline=profile[1:])

        fz, rx, rz = z0 + d.finial_center, d.finial_radius, d.finial_half_height
        n = d.curve_samples
        arc = [
            (rx * math.sin(t), fz - rz * math.cos(t))
            for t in (i * math.pi / n for i in range(1, n))
        ]
        finial = _revolve_profile((0, fz - rz), spline=arc + [(0, fz + rz)])
        head = head.union(finial)

        if d.slit:
            ex, ez = d.slit_inner[0], z0 + d.slit_inner[1]
            ox = d.slit_outer_x
            oz = ez - (ox - ex) * math.tan(math.radians(d.slit_angle))
            length = math.hypot(ox - ex, oz - ez)
            slit = (
                cq.Workplane()
                .box(length, 4 * self.body.base_radius, d.slit_width)
                .rotate((0, 0, 0), (0, 1, 0), d.slit_angle)
                .translate(((ex + ox) / 2, 0, (ez + oz) / 2))
            )
            head = head.cut(slit)
        return head


class StylizedQueen(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: QueenDimensions = QueenDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_radius(self) -> Optional[float]:
        return self.dimensions.shoulder_radius

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z0 = self.shoulder_top()
        neck = cylinder(d.neck_radius, z0, z0 + d.neck_height)
        bottom = z0 + d.crown_offset
        top = bottom + d.crown_height
        crown = _revolve_profile(
            (0, bottom),
            lines=[(d.crown_base_radius, bottom), (d.crown_top_radius, top), (0, top)],
        )
        half = d.notch_width / 2
        notch = (
            cq.Workplane("YZ")
            .polyline(
                [
                    (-half, top + d.notch_overcut),
                    (half, top + d.notch_overcut),
                    (0, top - d.notch_depth),
                ]
            )
            .close()
            .extrude(d.notch_length)
            .translate((d.notch_inner_radius, 0, 0))
        )
        step = 360.0 / d.notch_count
        for k in range(d.notch_count):
            crown = crown.cut(
                notch.rotate((0, 0, 0), (0, 0, 1), step * k + d.notch_phase)
            )
        return neck.union(crown)


class StylizedKing(AbstractStylizedChessPiece):
    def __init__(
        self,
        body: ChessBodyDimensions = ChessBodyDimensions(),
        dimensions: KingDimensions = KingDimensions(),
    ):
        super().__init__(body)
        self.dimensions = dimensions
        self._check()

    def stem_top_radius(self) -> float:
        return self.dimensions.stem_top_radius

    def shoulder_radius(self) -> Optional[float]:
        return self.dimensions.shoulder_radius

    def dimension_problems(self) -> List[str]:
        return self.dimensions.body_problems(self.body)

    def head(self) -> cq.Workplane:
        d = self.dimensions
        z0 = self.shoulder_top()
        head = (
            cylinder(d.head_radius, z0, z0 + d.head_height)
            .faces(">Z")
            .edges()
            .fillet(d.head_fillet)
        )
        top = z0 + d.head_height
        bar = (
            cq.Workplane()
            .box(
                d.bar_width,
                d.cross_thickness,
                d.bar_height,
                centered=(True, True, False),
            )
            .translate((0, 0, top))
        )
        arm = (
            cq.Workplane()
            .box(
                d.arm_span,
                d.cross_thickness,
                d.arm_height,
                centered=(True, True, False),
            )
            .translate((0, 0, top + d.arm_offset))
        )
        cross = bar.union(arm).translate((0, 0, -d.cross_embed))
        cross = _bevel_above(
            cross, top + self.body.bevel_clearance - d.cross_embed, d.bevel
        )
        return head.union(cross)
