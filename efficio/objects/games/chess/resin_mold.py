"""Printed masters and cottle for the keyed clear-resin cylinders.

Cast orientation: notch DOWN (a tapered silicone plug rises from the mold
floor), key boss UP (narrow end up, so it pours and demolishes), pour funnel on
the boss.  The piece stands on a silicone pin moulded into the plug tip.

Part coordinates: master axis +Z with the key long axis on X.  Mold coordinates
(frame, plate, lid, blocks) come from :func:`lying`: master axis -> +X, key long
axis -> +Y, parting plane z = 0.  Every size comes from a
:class:`~efficio.objects.games.chess.resin_geometry.ResinMoldPlan`.
"""

import math
from typing import List, Optional, Tuple

import cadquery as cq

from efficio.objects.base import Color, EfficioObject
from efficio.objects.games.chess.pieces import AbstractStylizedChessPiece
from efficio.objects.games.chess.resin_geometry import ResinMoldPlan
from efficio.objects.profiles import box, cylinder, wrap
from efficio.objects.shapes import Shape

ColoredPart = Tuple[str, cq.Shape, Color]

CLEAR_COLOR: Color = (150, 200, 230)
MASTER_COLOR: Color = (205, 140, 70)
FRAME_COLOR: Color = (120, 130, 145)
PLATE_COLOR: Color = (95, 105, 120)
BLOCK_A_COLOR: Color = (70, 150, 120)
BLOCK_B_COLOR: Color = (190, 100, 130)
LID_COLOR: Color = (170, 170, 90)
SILICONE_COLOR: Color = (230, 215, 170)
PIECE_COLOR: Color = (200, 60, 60)
SCREW_COLOR: Color = (230, 230, 235)


def shape_of(wp: cq.Workplane) -> cq.Shape:
    """The single CadQuery shape a workplane holds (typed; fails if it is not one)."""
    value = wp.val()
    if not isinstance(value, cq.Shape):
        raise ValueError("workplane does not hold a shape")
    return value


def _oval(
    length: float, width: float, z: float, height: float, taper: float = 0.0
) -> cq.Workplane:
    """Slot-shaped prism from z; negative height extrudes downward."""
    return (
        cq.Workplane("XY")
        .workplane(offset=z)
        .slot2D(length, width)
        .extrude(height, taper=taper)
    )


def _along(
    radius: float,
    length: float,
    point: Tuple[float, float, float],
    axis: Tuple[float, float, float],
) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(radius, length, cq.Vector(*point), cq.Vector(*axis))
    return cq.Workplane("XY").newObject([solid])


def lying(wp: cq.Workplane) -> cq.Workplane:
    """Master axis -> +X, key long axis -> +Y (parting plane z = 0)."""
    return wp.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (0, 1, 0), 90)


# -- master pieces ------------------------------------------------------------
def cast_body(plan: ResinMoldPlan) -> cq.Workplane:
    """What the resin makes: cylinder, boss up, notch down (no funnel, no pin hole)."""
    r, k = plan.resin, plan.resin.key
    h = plan.body_height
    cyl = (
        cylinder(r.radius, 0, h)
        .faces(">Z")
        .edges()
        .chamfer(r.chamfer)
        .faces("<Z")
        .edges()
        .chamfer(r.chamfer)
    )
    boss = _oval(k.length, k.width, h, k.boss_height, k.taper_degrees)
    notch = _oval(
        k.length + k.clearance, k.width + k.clearance, 0, k.notch_depth, k.taper_degrees
    )
    return cyl.union(boss).cut(notch)


def _pin_hole(plan: ResinMoldPlan) -> cq.Workplane:
    r = plan.resin
    return cylinder(
        r.pin_diameter / 2, r.key.notch_depth, r.key.notch_depth + r.pin_height
    )


def _funnel_flare(plan: ResinMoldPlan) -> cq.Workplane:
    """Funnel at the origin (z = 0 .. funnel height) with M3 pilots on both poles."""
    s, h = plan.split, plan.hold_down
    tip_length, tip_width = plan.resin.key.tip_size()
    flare = _oval(tip_length, tip_width, 0, s.funnel_height, -s.funnel_flare_degrees)
    z = s.funnel_height - h.from_face
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * h.offset
            point = (x, sy * h.spot_distance, z)
            flare = flare.cut(_along(h.spot_diameter / 2, 30.0, point, (0, sy, 0)))
            flare = flare.cut(
                _along(h.tap_drill / 2, h.pilot_depth, point, (0, -sy, 0))
            )
    return flare


def master(plan: ResinMoldPlan) -> cq.Workplane:
    """One-piece master: cast body, pour funnel on the boss, pin hole in the notch roof."""
    top = plan.body_height + plan.resin.key.boss_height
    funnel = _funnel_flare(plan).translate((0, 0, top))
    return cast_body(plan).union(funnel).cut(_pin_hole(plan))


def _peg(plan: ResinMoldPlan, z: float, up: bool = True) -> cq.Workplane:
    s = plan.split
    return _oval(s.peg_length, s.peg_width, z, s.peg_height if up else -s.peg_height)


def _socket(plan: ResinMoldPlan, z: float, up: bool = True) -> cq.Workplane:
    s = plan.split
    depth = s.socket_depth()
    return _oval(
        s.peg_length + s.peg_fit,
        s.peg_width + s.peg_fit,
        z,
        depth if up else -depth,
    )


def master_bottom_cap(plan: ResinMoldPlan) -> cq.Workplane:
    """Notch end: notch opening at z = 0, pin hole in its roof, peg on top."""
    r, k, s = plan.resin, plan.resin.key, plan.split
    cyl = (
        cylinder(r.radius, 0, s.bottom_cap_height)
        .faces("<Z")
        .edges()
        .chamfer(r.chamfer)
    )
    notch = _oval(
        k.length + k.clearance, k.width + k.clearance, 0, k.notch_depth, k.taper_degrees
    )
    return cyl.cut(notch).cut(_pin_hole(plan)).union(_peg(plan, s.bottom_cap_height))


def master_spacer(plan: ResinMoldPlan) -> cq.Workplane:
    """Plain cylinder that sets the piece's height: socket below, peg above."""
    length = plan.spacer_length
    cyl = cylinder(plan.resin.radius, 0, length)
    return cyl.cut(_socket(plan, 0)).union(_peg(plan, length))


def master_top_cap(plan: ResinMoldPlan) -> cq.Workplane:
    """Boss end: socket underneath, boss on top with a socket in its tip."""
    r, k, s = plan.resin, plan.resin.key, plan.split
    cyl = cylinder(r.radius, 0, s.top_cap_height).faces(">Z").edges().chamfer(r.chamfer)
    boss = _oval(k.length, k.width, s.top_cap_height, k.boss_height, k.taper_degrees)
    return (
        cyl.union(boss)
        .cut(_socket(plan, 0))
        .cut(_socket(plan, s.top_cap_height + k.boss_height, up=False))
    )


def master_funnel(plan: ResinMoldPlan) -> cq.Workplane:
    """Pour funnel with a peg underneath (modelled as assembled: peg down, flare up)."""
    return _funnel_flare(plan).union(_peg(plan, 0, up=False))


def _master_offsets(plan: ResinMoldPlan) -> Tuple[float, float, float]:
    """z of the spacer, top cap and funnel in the assembled master."""
    bottom = plan.split.bottom_cap_height
    return (
        bottom,
        bottom + plan.spacer_length,
        plan.body_height + plan.resin.key.boss_height,
    )


def assembled_master(plan: ResinMoldPlan) -> cq.Workplane:
    """All four printed parts at their assembled positions."""
    spacer_z, top_z, funnel_z = _master_offsets(plan)
    return (
        master_bottom_cap(plan)
        .union(master_spacer(plan).translate((0, 0, spacer_z)))
        .union(master_top_cap(plan).translate((0, 0, top_z)))
        .union(master_funnel(plan).translate((0, 0, funnel_z)))
    )


# -- cottle -------------------------------------------------------------------
def _x_range(plan: ResinMoldPlan) -> Tuple[float, float, float]:
    x0, x1 = -plan.cottle.silicone_wall, plan.master_length
    return x0, x1, (x0 + x1) / 2


def _centered(size: Tuple[float, float, float], cx: float, z: float) -> cq.Workplane:
    return cq.Workplane("XY").box(*size).translate((cx, 0, z))


def cottle_frame(plan: ResinMoldPlan) -> cq.Workplane:
    """Open-top, open-bottom rectangular sleeve around the master."""
    x0, x1, cx = _x_range(plan)
    inner_len = x1 - x0
    wall = plan.cottle.frame_wall
    outer = _centered(
        (inner_len + 2 * wall, 2 * plan.half_width + 2 * wall, 2 * plan.half_height),
        cx,
        0,
    )
    inner = _centered((inner_len, 2 * plan.half_width, 2 * plan.half_height), cx, 0)
    return outer.cut(inner)


def cottle_plate(plan: ResinMoldPlan) -> cq.Workplane:
    """Base plate: the frame and blocks stand in a shallow recess; screws come from below."""
    c, h = plan.cottle, plan.hold_down
    x0, x1, cx = _x_range(plan)
    outline_x = x1 - x0 + 2 * c.frame_wall
    outline_y = 2 * plan.half_width + 2 * c.frame_wall
    top = plan.plate_bottom + c.plate_thickness
    slab = box(
        cx - outline_x / 2 - c.plate_margin,
        cx + outline_x / 2 + c.plate_margin,
        -outline_y / 2 - c.plate_margin,
        outline_y / 2 + c.plate_margin,
        plan.plate_bottom,
        top,
    )
    recess = box(
        cx - (outline_x + c.recess_clearance) / 2,
        cx + (outline_x + c.recess_clearance) / 2,
        -(outline_y + c.recess_clearance) / 2,
        (outline_y + c.recess_clearance) / 2,
        top - c.recess_depth,
        top + 1,
    )
    plate = slab.cut(recess)
    for x, y in plan.mount_points():
        plate = plate.cut(
            _along(
                h.clearance_hole / 2,
                c.plate_thickness + 2,
                (x, y, plan.plate_bottom - 1),
                (0, 0, 1),
            )
        )
        plate = plate.cut(
            _along(
                h.counterbore_diameter / 2,
                h.counterbore_depth + 1,
                (x, y, plan.plate_bottom - 1),
                (0, 0, 1),
            )
        )
    return plate


def _screw_channels(block: cq.Workplane, plan: ResinMoldPlan) -> cq.Workplane:
    """Clear the screw path down from the pilot bottom.

    The block fills every void in the master, including the Ø2.5 pilot, so the
    channel must start where the pilot ends or the screw would hit that stud.
    """
    h = plan.hold_down
    start = h.pilot_depth - h.spot_distance
    for x, y in plan.mount_points():
        block = block.cut(
            _along(
                h.clearance_hole / 2,
                plan.half_height + start + 1.0,
                (x, y, start),
                (0, 0, -1),
            )
        )
    return block


def _block_blank(plan: ResinMoldPlan) -> cq.Workplane:
    c = plan.cottle
    x0, x1, cx = _x_range(plan)
    size = (
        x1 - x0 - c.block_clearance,
        2 * plan.half_width - c.block_clearance,
        plan.half_height,
    )
    return _centered(size, cx, -plan.half_height / 2)


def _registration_points(plan: ResinMoldPlan) -> List[Tuple[float, float]]:
    c = plan.cottle
    x0, x1, _ = _x_range(plan)
    y = plan.resin.radius + c.registration_offset
    xs = (x0 + c.registration_from_base, x1 - c.registration_from_funnel)
    return [(x, sy * y) for x in xs for sy in (-1, 1)]


def cottle_block_a(plan: ResinMoldPlan) -> cq.Workplane:
    """Parting block holding the lower half of the master, with registration bumps."""
    block = _block_blank(plan).cut(lying(master(plan)))
    for x, y in _registration_points(plan):
        bump = cq.Workplane("XY").sphere(plan.cottle.registration_radius)
        block = block.union(bump.translate((x, y, 0)))
    return _screw_channels(block, plan)


def cottle_block_b(plan: ResinMoldPlan) -> cq.Workplane:
    """Inverse block for the second pour: master turned 180 deg about its axis,
    dimples that cast bumps on half B to seat in the dimples block A left in half A."""
    c = plan.cottle
    block = _block_blank(plan).cut(
        lying(master(plan)).rotate((0, 0, 0), (1, 0, 0), 180)
    )
    for x, y in _registration_points(plan):
        dimple = cq.Workplane("XY").sphere(
            c.registration_radius + c.registration_clearance
        )
        block = block.cut(dimple.translate((x, y, 0)))
    return _screw_channels(block, plan)


def cottle_lid(plan: ResinMoldPlan) -> cq.Workplane:
    """Level lid: sits on the frame rim so the silicone is exactly half_height above
    the parting plane.  Pour through the slot; silicone showing in every vent means full.
    """
    c = plan.cottle
    x0, x1, cx = _x_range(plan)
    top = plan.half_height
    lid = _centered(
        (
            x1 - x0 + 2 * c.frame_wall,
            2 * plan.half_width + 2 * c.frame_wall,
            c.lid_thickness,
        ),
        cx,
        top + c.lid_thickness / 2,
    )
    lip = _centered(
        (
            x1 - x0 - c.lid_lip_clearance,
            2 * plan.half_width - c.lid_lip_clearance,
            c.lid_lip,
        ),
        cx,
        top - c.lid_lip / 2,
    )
    lid = lid.union(lip)
    through = c.lid_thickness + c.lid_lip
    slot = (
        cq.Workplane("XY")
        .workplane(offset=top - c.lid_lip)
        .center(c.pour_slot_x, 0)
        .slot2D(c.pour_slot_length, c.pour_slot_width, 90)
        .extrude(through)
    )
    lid = lid.cut(slot)
    vent_y = plan.resin.radius + c.vent_offset
    for vx in (plan.master_length / 2, plan.master_length - c.vent_end_inset):
        for sy in (-1, 1):
            vent = (
                cq.Workplane("XY")
                .workplane(offset=top - c.lid_lip)
                .center(vx, sy * vent_y)
                .circle(c.vent_diameter / 2)
                .extrude(through)
            )
            lid = lid.cut(vent)
    return lid


def silicone_per_half_ml(plan: ResinMoldPlan) -> float:
    """Silicone for ONE half (the other half is identical), registration bumps deducted."""
    c = plan.cottle
    inner = plan.mold_length * 2 * plan.half_width * plan.half_height
    box = cq.Workplane("XY").box(500, 500, 500).translate((0, 0, 250))
    upper = shape_of(lying(master(plan)).intersect(box)).Volume()
    bumps = (
        len(_registration_points(plan))
        * (2.0 / 3.0)
        * math.pi
        * c.registration_radius**3
    )
    return (inner - upper - bumps) / 1000.0


def hold_down_screw(plan: ResinMoldPlan, index: int) -> cq.Workplane:
    """Plain cylinder standing in for one M3 screw (shank only) for previews and fit checks."""
    h = plan.hold_down
    x, y = plan.mount_points()[index]
    return _along(
        h.fastener.spec.major_diameter / 2,
        h.screw_length,
        (x, y, plan.screw_seat),
        (0, 0, 1),
    )


# -- EfficioObjects -----------------------------------------------------------
class _ResinTool(EfficioObject):
    """Common base: a part defined by one :class:`ResinMoldPlan`."""

    def __init__(self, plan: ResinMoldPlan = ResinMoldPlan()):
        problems = plan.problems()
        if problems:
            raise ValueError("; ".join(problems))
        self.plan = plan

    def solid(self) -> cq.Workplane:
        raise NotImplementedError

    def shape(self) -> Optional[Shape]:
        return wrap(self.solid())


class ResinCylinder(_ResinTool):
    """The clear cast cylinder (boss up, notch down), without the piece."""

    def solid(self) -> cq.Workplane:
        return cast_body(self.plan)


class ResinMaster(_ResinTool):
    """One-piece master (reference; print the modular parts instead)."""

    def solid(self) -> cq.Workplane:
        return master(self.plan)


class ResinMasterBottomCap(_ResinTool):
    def solid(self) -> cq.Workplane:
        return master_bottom_cap(self.plan)


class ResinMasterSpacer(_ResinTool):
    def solid(self) -> cq.Workplane:
        return master_spacer(self.plan)


class ResinMasterTopCap(_ResinTool):
    def solid(self) -> cq.Workplane:
        return master_top_cap(self.plan)


class ResinMasterFunnel(_ResinTool):
    """Print large face down: the 35 degree flare needs no support."""

    def solid(self) -> cq.Workplane:
        return master_funnel(self.plan)

    def print_solid(self) -> cq.Workplane:
        """Flare opening on the bed (flipped about X)."""
        top = self.plan.split.funnel_height
        return self.solid().rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, top))


class ResinMoldFrame(_ResinTool):
    def solid(self) -> cq.Workplane:
        return cottle_frame(self.plan)


class ResinMoldPlate(_ResinTool):
    def solid(self) -> cq.Workplane:
        return cottle_plate(self.plan)


class ResinMoldLid(_ResinTool):
    def solid(self) -> cq.Workplane:
        return cottle_lid(self.plan)


class ResinMoldBlockA(_ResinTool):
    def solid(self) -> cq.Workplane:
        return cottle_block_a(self.plan)


class ResinMoldBlockB(_ResinTool):
    def solid(self) -> cq.Workplane:
        return cottle_block_b(self.plan)


def _half_space(upper: bool = True, y: float = 0.0) -> cq.Workplane:
    """Big box on the y > ``y`` (or y < ``y``) side, used to open a section view."""
    size = 400.0
    return (
        cq.Workplane("XY")
        .box(size, size, size)
        .translate((0, y + (size / 2 if upper else -size / 2), 0))
    )


class ResinMasterAssembly(_ResinTool):
    """The four printed master parts at assembled positions, each its own colour."""

    PART_COLORS = (
        (180, 120, 60),
        (205, 150, 80),
        (225, 175, 110),
        (160, 100, 50),
    )

    def solid(self) -> cq.Workplane:
        return assembled_master(self.plan)

    def preview_parts(self, current: Color) -> List[ColoredPart]:
        spacer_z, top_z, funnel_z = _master_offsets(self.plan)
        pieces = [
            ("bottom cap", master_bottom_cap(self.plan), 0.0),
            ("spacer", master_spacer(self.plan), spacer_z),
            ("top cap", master_top_cap(self.plan), top_z),
            ("funnel", master_funnel(self.plan), funnel_z),
        ]
        return [
            (name, shape_of(wp.translate((0, 0, z))), color)
            for (name, wp, z), color in zip(pieces, self.PART_COLORS)
        ]

    def preview_legend(self, current: Color) -> List[Tuple[str, Color]]:
        names = ("bottom cap", "spacer", "top cap", "funnel")
        return list(zip(names, self.PART_COLORS))


class ResinPieceCast(EfficioObject):
    """A chess piece embedded in its resin cylinder, opened by a section.

    ``piece`` is any :class:`AbstractStylizedChessPiece`; the cylinder height is
    derived from the piece's own height, so the same plan builds every piece.
    """

    def __init__(
        self, piece: AbstractStylizedChessPiece, plan: Optional[ResinMoldPlan] = None
    ):
        self.piece = piece
        solid = piece.solid()
        height = shape_of(solid).BoundingBox().zmax
        base_radius = piece.body.base_radius
        self.plan = plan or ResinMoldPlan(
            piece_height=height, piece_base_radius=base_radius
        )
        problems = self.plan.problems()
        if problems:
            raise ValueError("; ".join(problems))
        self._piece_solid = solid

    def _placed_piece(self) -> cq.Workplane:
        return self._piece_solid.translate((0, 0, self.plan.resin.piece_z))

    def solid(self) -> cq.Workplane:
        return cast_body(self.plan).cut(self._placed_piece())

    def shape(self) -> Optional[Shape]:
        return wrap(self.solid())

    def preview_parts(self, current: Color) -> List[ColoredPart]:
        opening = _half_space(upper=False)  # y < 0 is removed; y > 0 stays
        resin = self.solid().cut(opening)
        piece = self._placed_piece().cut(opening)
        return [
            ("resin", shape_of(resin), CLEAR_COLOR),
            ("piece", shape_of(piece), PIECE_COLOR),
        ]

    def preview_legend(self, current: Color) -> List[Tuple[str, Color]]:
        return [("clear resin", CLEAR_COLOR), ("piece", PIECE_COLOR)]


class ResinMoldSetup(_ResinTool):
    """Cottle for one pour: ``"A"`` (first half) or ``"B"`` (after removing the master).

    The preview shows the plate, frame, parting block, master (pour A only,
    as the master stays in block A), screws and the lid, cut open along y = 0
    so the screw bite and silicone level are visible.
    """

    def __init__(
        self,
        plan: ResinMoldPlan = ResinMoldPlan(),
        pour: str = "A",
        section_y: float = 0.0,
    ):
        super().__init__(plan)
        self.section_y = section_y
        if pour not in ("A", "B"):
            raise ValueError("pour must be 'A' or 'B'")
        self.pour = pour

    def _master_in_block(self) -> cq.Workplane:
        wp = lying(master(self.plan))
        return wp if self.pour == "A" else wp.rotate((0, 0, 0), (1, 0, 0), 180)

    def solid(self) -> cq.Workplane:
        block = cottle_block_a if self.pour == "A" else cottle_block_b
        stack = (
            cottle_plate(self.plan)
            .union(cottle_frame(self.plan))
            .union(block(self.plan))
        )
        return stack.union(self._master_in_block())

    def preview_parts(self, current: Color) -> List[ColoredPart]:
        plan = self.plan
        opening = _half_space(upper=False, y=self.section_y)
        block = cottle_block_a if self.pour == "A" else cottle_block_b
        items: List[Tuple[str, cq.Workplane, Color]] = [
            ("plate", cottle_plate(plan), PLATE_COLOR),
            ("frame", cottle_frame(plan), FRAME_COLOR),
            (
                f"block {self.pour}",
                block(plan),
                BLOCK_A_COLOR if self.pour == "A" else BLOCK_B_COLOR,
            ),
            ("master", self._master_in_block(), MASTER_COLOR),
        ]
        items += [
            (f"M3 screw {i + 1}", hold_down_screw(plan, i), SCREW_COLOR)
            for i in range(len(plan.mount_points()))
        ]
        cut = [(name, wp.cut(opening), color) for name, wp, color in items]
        return [
            (name, shape_of(wp), color)
            for name, wp, color in cut
            if shape_of(wp).Volume() > 1e-6
        ]

    def preview_legend(self, current: Color) -> List[Tuple[str, Color]]:
        block_color = BLOCK_A_COLOR if self.pour == "A" else BLOCK_B_COLOR
        return [
            ("plate", PLATE_COLOR),
            ("frame", FRAME_COLOR),
            (f"block {self.pour}", block_color),
            ("master", MASTER_COLOR),
            ("M3 screws", SCREW_COLOR),
        ]
