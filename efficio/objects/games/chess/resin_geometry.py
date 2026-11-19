"""Pure dimensions for the keyed resin cylinder and its mold tooling (no CadQuery).

All lengths are millimetres.  The cast cylinder stands on its bottom face with
the key *boss* up and the matching *notch* in the bottom face, so one piece
sits on the next.  The printed master is cast boss-up (narrow end up) so the
silicone pours and demolds; the notch is formed by a tapered silicone plug.

Master axis is +Z, key long axis is +X.  Mold coordinates (``ResinMoldPlan``)
lay the master on its side: axis -> +X, key long axis -> +Y, key short axis ->
+Z, parting plane z = 0.

Declared walls: the printed tooling, the silicone and the cast resin each carry
a provisional :class:`~efficio.objects.walls.WallPolicy`.  A pass means the
declared measurements meet declared limits, nothing more.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.fits import Process
from efficio.objects.games.chess.geometry import _positive, _Validated
from efficio.objects.walls import WallPolicy

DEFAULT_SCREW_CLEARANCE = 0.2  # radial; matches efficio's DEFAULT_FASTENER_CLEARANCE


@dataclass(frozen=True)
class KeyDimensions(_Validated):
    """Oval boss with tapered sides and the notch that receives it."""

    length: float = 28.0  # boss long axis at its root
    width: float = 16.0  # boss short axis at its root
    taper_degrees: float = 12.0  # each side, narrowing away from the cylinder
    boss_height: float = 6.0
    notch_depth: float = 6.0
    clearance: float = 0.4  # notch is this much longer and wider than the boss

    def tip_size(self) -> Tuple[float, float]:
        """(length, width) of the boss tip."""
        shrink = 2 * self.boss_height * math.tan(math.radians(self.taper_degrees))
        return self.length - shrink, self.width - shrink

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("clearance",))
        if problems:
            return problems
        if self.clearance < 0:
            problems.append("clearance must not be negative")
        if not 0 < self.taper_degrees < 45:
            problems.append("taper_degrees must be between 0 and 45")
        elif min(self.tip_size()) <= 0:
            problems.append("taper consumes the boss tip")
        if self.width >= self.length:
            problems.append("key must be oval: longer than it is wide")
        if self.notch_depth < self.boss_height:
            problems.append("notch must be at least as deep as the boss is tall")
        return problems


@dataclass(frozen=True)
class ResinCylinderDimensions(_Validated):
    """Clear cast cylinder around a piece (38 mm for 1.75 in board squares)."""

    radius: float = 19.0
    floor: float = 3.0  # clear resin between notch roof and the piece base
    cover: float = 3.0  # clear resin over the head
    chamfer: float = 1.0
    key: KeyDimensions = KeyDimensions()
    pin_diameter: float = 8.4  # silicone pin that carries the piece (press fit)
    pin_height: float = 8.0  # floor + socket depth of the piece base

    @property
    def piece_z(self) -> float:
        """Height of the piece base above the cylinder's bottom face."""
        return self.key.notch_depth + self.floor

    def body_height(self, piece_height: float) -> float:
        """Cylinder height without the boss."""
        return self.piece_z + piece_height + self.cover

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("key",))
        if problems:
            return problems
        if self.chamfer >= self.radius:
            problems.append("chamfer is too large for the cylinder")
        if (self.key.length + self.key.clearance) / 2 >= self.radius - self.chamfer:
            problems.append("notch must stay inside the cylinder wall")
        if self.pin_height <= self.floor:
            problems.append("pin must be taller than the floor to reach the socket")
        return problems

    def wall_measurements(self, piece_base_radius: float) -> Dict[str, float]:
        """Clear-resin section thicknesses checked against RESIN_WALL_POLICY."""
        return {
            "resin_ring_around_base": self.radius - piece_base_radius,
            "resin_floor_under_piece": self.floor,
            "resin_cover_over_head": self.cover,
            "resin_beside_notch": self.radius
            - (self.key.length + self.key.clearance) / 2,
        }


@dataclass(frozen=True)
class MasterSplitDimensions(_Validated):
    """How the printed master divides: bottom cap, spacer, top cap, funnel."""

    bottom_cap_height: float = 18.0  # notch end: notch plus the pin hole above it
    top_cap_height: float = 12.0  # cylinder section under the boss
    peg_length: float = 14.0  # oval alignment peg between parts
    peg_width: float = 8.0
    peg_height: float = 5.0
    peg_fit: float = 0.4  # socket is this much longer and wider than the peg
    socket_extra: float = 0.2  # socket is this much deeper than the peg is tall
    funnel_height: float = 10.0
    funnel_flare_degrees: float = 35.0  # printable without support
    min_wall: float = 2.0  # least material left around a peg socket

    def socket_depth(self) -> float:
        return self.peg_height + self.socket_extra

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("peg_fit", "socket_extra"))
        if problems:
            return problems
        if self.peg_fit < 0 or self.socket_extra < 0:
            problems.append("peg_fit and socket_extra must not be negative")
        if self.peg_width >= self.peg_length:
            problems.append("peg must be oval: longer than it is wide")
        if self.funnel_flare_degrees >= 60:
            problems.append("funnel flare steeper than 60 degrees will not print")
        return problems

    def spacer_length(
        self, resin: ResinCylinderDimensions, piece_height: float
    ) -> float:
        return (
            resin.body_height(piece_height)
            - self.bottom_cap_height
            - self.top_cap_height
        )

    def body_problems(
        self, resin: ResinCylinderDimensions, piece_height: float
    ) -> List[str]:
        problems = []
        if self.bottom_cap_height < (
            resin.key.notch_depth + resin.pin_height + self.min_wall
        ):
            problems.append("bottom cap is too short for the notch and pin hole")
        if (
            self.spacer_length(resin, piece_height)
            < self.socket_depth() + self.min_wall
        ):
            problems.append("spacer is too short for its peg socket")
        tip_length, tip_width = resin.key.tip_size()
        if (
            self.peg_length + self.peg_fit > tip_length - 2 * self.min_wall
            or self.peg_width + self.peg_fit > tip_width - 2 * self.min_wall
        ):
            problems.append("peg socket leaves too little wall in the boss tip")
        if self.socket_depth() > resin.key.boss_height + self.top_cap_height - 1:
            problems.append("top cap is too short for the tip and base sockets")
        return problems

    def funnel_top_size(self, resin: ResinCylinderDimensions) -> Tuple[float, float]:
        """(length, width) of the funnel's wide, open end."""
        tip_length, tip_width = resin.key.tip_size()
        grow = (
            2 * self.funnel_height * math.tan(math.radians(self.funnel_flare_degrees))
        )
        return tip_length + grow, tip_width + grow


@dataclass(frozen=True)
class HoldDownDimensions(_Validated):
    """Self-tapping screws from below into pilot holes in the funnel.

    Holes live in the funnel only: a hole in the body would leave a stud on the
    cavity wall and a pit in the resin, while the funnel is trimmed off.  Hole
    sizes come from the fastener's ISO catalogue entry.
    """

    fastener: MetricThread = MetricThread.M3
    offset: float = 8.0  # each side of the funnel centre, along the key long axis
    from_face: float = 3.0  # pilot axis this far in from the funnel's flat face
    spot_distance: float = 9.5  # flat spot-face plane, each pole, from the axis
    spot_diameter: float = 4.5
    pilot_depth: float = 6.5  # blind; solid is left between the two poles
    counterbore_depth: float = 5.0  # plate underside recess for the head
    screw_length: float = 25.0
    head_clearance: float = DEFAULT_SCREW_CLEARANCE  # radial
    min_engagement_diameters: float = 1.5  # bite, in screw diameters

    @property
    def clearance_hole(self) -> float:
        return self.fastener.spec.clearance_hole

    @property
    def tap_drill(self) -> float:
        return self.fastener.spec.tap_drill

    @property
    def counterbore_diameter(self) -> float:
        return self.fastener.spec.head_diameter + 2 * self.head_clearance

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("fastener", "head_clearance"))
        if problems:
            return problems
        spec = self.fastener.spec
        if self.head_clearance < 0:
            problems.append("head_clearance must not be negative")
        if self.spot_distance - self.pilot_depth < 2.0:
            problems.append("pilot must stop at least 2 mm short of the axis")
        if self.spot_diameter < self.tap_drill + 1.0:
            problems.append("spot face must be wider than the pilot by 1 mm")
        if self.counterbore_depth < spec.head_height:
            problems.append("counterbore must be deep enough to hide the head")
        return problems


@dataclass(frozen=True)
class CottleDimensions(_Validated):
    """Printed frame, plate, lid and parting blocks around the master."""

    silicone_wall: float = 8.0  # silicone around the master on every side
    frame_wall: float = 3.0
    plate_thickness: float = 9.0
    plate_margin: float = 4.0  # plate extends this far past the frame
    recess_depth: float = 2.0  # the frame stands in a recess in the plate
    recess_clearance: float = 0.4  # total, recess vs frame outline
    block_clearance: float = 0.4  # total, block vs frame opening
    lid_thickness: float = 4.0
    lid_lip: float = 2.0
    lid_lip_clearance: float = 0.6  # total, lip vs frame opening
    pour_slot_length: float = 24.0
    pour_slot_width: float = 7.0
    pour_slot_x: float = -3.5  # centre, over the silicone strip at the base end
    vent_diameter: float = 3.0
    vent_offset: float = 5.0  # vent centres this far outside the cylinder radius
    vent_end_inset: float = 4.0  # funnel-end vents from the end wall
    registration_radius: float = 3.0
    registration_offset: float = 4.5  # hemispheres this far outside the cylinder
    registration_clearance: float = 0.2  # radial, dimples vs bumps
    registration_from_base: float = 6.0
    registration_from_funnel: float = 8.0

    def problems(self) -> List[str]:
        non_negative = (
            "pour_slot_x",
            "recess_clearance",
            "block_clearance",
            "lid_lip_clearance",
            "registration_clearance",
        )
        problems = _positive(self, exempt=non_negative)
        if problems:
            return problems
        for name in non_negative:
            if name != "pour_slot_x" and getattr(self, name) < 0:
                problems.append(f"{name} must not be negative")
        if self.recess_depth >= self.plate_thickness:
            problems.append("recess must be shallower than the plate")
        if not (
            -self.silicone_wall <= self.pour_slot_x - self.pour_slot_width / 2
            and self.pour_slot_x + self.pour_slot_width / 2 <= 0
        ):
            problems.append("pour slot must lie over the base-end silicone strip")
        return problems


# Declared wall budgets.  Numbers are provisional geometry floors, not
# calculated design limits; see docs/wall-policy.md for the convention.
PRINTED_TOOLING_WALL_POLICY = WallPolicy(
    material="PETG, 0.4 mm nozzle, perimeters filling the wall",
    process=Process.FDM_PRINT,
    environment="room-temperature silicone pour, ~54 mm liquid head, hand handling",
    minimum_mm=2.0,
    basis="provisional printability floor (about five perimeters); not a strength limit",
    required_features=(
        "frame_wall",
        "plate_below_recess",
        "plate_above_counterbore",
        "lid_thickness",
        "boss_tip_wall_at_socket",
        "funnel_solid_between_pilots",
    ),
)

SILICONE_WALL_POLICY = WallPolicy(
    material="addition- or condensation-cure silicone (product unselected)",
    process=Process.RESIN_CAST,
    environment="two-part mold held in rubber bands or a clamp, resin poured at room temperature",
    minimum_mm=6.0,
    basis="provisional geometry floor from common 6-10 mm mold practice; tear and flex untested",
    required_features=(
        "silicone_over_crest",
        "silicone_at_base_end",
        "silicone_beside_funnel",
    ),
)

RESIN_WALL_POLICY = WallPolicy(
    material="clear casting resin (grade unselected)",
    process=Process.RESIN_CAST,
    environment="indoor game pieces; handling and stacking, no pressure or sustained clamp load",
    minimum_mm=3.0,
    basis="provisional geometry floor; impact, creep and yellowing untested",
    required_features=(
        "resin_ring_around_base",
        "resin_floor_under_piece",
        "resin_cover_over_head",
        "resin_beside_notch",
    ),
)


@dataclass(frozen=True)
class ResinMoldPlan(_Validated):
    """Everything needed to size the master and cottle for one piece."""

    piece_height: float = 28.0
    piece_base_radius: float = 16.0
    resin: ResinCylinderDimensions = ResinCylinderDimensions()
    split: MasterSplitDimensions = MasterSplitDimensions()
    hold_down: HoldDownDimensions = HoldDownDimensions()
    cottle: CottleDimensions = CottleDimensions()

    # -- sizes ---------------------------------------------------------------
    @property
    def body_height(self) -> float:
        return self.resin.body_height(self.piece_height)

    @property
    def master_length(self) -> float:
        """Axial length of the full master, funnel included."""
        return self.body_height + self.resin.key.boss_height + self.split.funnel_height

    @property
    def spacer_length(self) -> float:
        return self.split.spacer_length(self.resin, self.piece_height)

    @property
    def half_height(self) -> float:
        """Mold extent above and below the parting plane."""
        return self.resin.radius + self.cottle.silicone_wall

    @property
    def half_width(self) -> float:
        return self.resin.radius + self.cottle.silicone_wall

    @property
    def mold_length(self) -> float:
        """Silicone block length: master plus the base-end strip."""
        return self.master_length + self.cottle.silicone_wall

    @property
    def plate_bottom(self) -> float:
        return -self.half_height - (
            self.cottle.plate_thickness - self.cottle.recess_depth
        )

    @property
    def screw_seat(self) -> float:
        """z of the screw head's bearing face in the plate counterbore."""
        return self.plate_bottom + self.hold_down.counterbore_depth

    @property
    def screw_tip(self) -> float:
        return self.screw_seat + self.hold_down.screw_length

    @property
    def screw_engagement(self) -> float:
        """How far the screw bites into the funnel past the spot-face plane."""
        return self.screw_tip + self.hold_down.spot_distance

    def screw_length_window(self) -> Tuple[float, float]:
        """(shortest, longest) screw that bites enough without bottoming in the pilot."""
        h = self.hold_down
        shortest = (
            h.min_engagement_diameters * h.fastener.spec.major_diameter
            - h.spot_distance
            - self.screw_seat
        )
        longest = h.pilot_depth - h.spot_distance - 0.5 - self.screw_seat
        return shortest, longest

    def mount_points(self) -> List[Tuple[float, float]]:
        """Mold-frame (x, y) of the two hold-down screws (they run along z)."""
        x = self.master_length - self.hold_down.from_face
        return [(x, -self.hold_down.offset), (x, self.hold_down.offset)]

    # -- checks --------------------------------------------------------------
    def problems(self) -> List[str]:
        problems = _positive(
            self,
            exempt=("resin", "split", "hold_down", "cottle"),
        )
        if problems:
            return problems
        problems += self.split.body_problems(self.resin, self.piece_height)
        if self.piece_base_radius >= self.resin.radius:
            problems.append("piece base must fit inside the cylinder")
        h = self.hold_down
        shortest, longest = self.screw_length_window()
        if not shortest <= h.screw_length <= longest:
            problems.append(
                f"screw_length {h.screw_length:g} must be between "
                f"{shortest:g} and {longest:g} mm (bite enough, do not bottom out)"
            )
        if (
            self.cottle.plate_thickness - self.cottle.recess_depth - h.counterbore_depth
            <= 0
        ):
            problems.append("counterbore breaks through the plate")
        half_spot = h.spot_diameter / 2
        if not (half_spot < h.from_face < self.split.funnel_height - half_spot):
            problems.append("spot face must lie inside the funnel height")
        problems += RESIN_WALL_POLICY.violations(
            self.resin.wall_measurements(self.piece_base_radius)
        )
        problems += PRINTED_TOOLING_WALL_POLICY.violations(
            self.printed_wall_measurements()
        )
        problems += SILICONE_WALL_POLICY.violations(self.silicone_wall_measurements())
        return problems

    def silicone_wall_measurements(self) -> Dict[str, float]:
        funnel_length, _ = self.split.funnel_top_size(self.resin)
        return {
            "silicone_over_crest": self.cottle.silicone_wall,
            "silicone_at_base_end": self.cottle.silicone_wall,
            "silicone_beside_funnel": self.half_width - funnel_length / 2,
        }

    def printed_wall_measurements(self) -> Dict[str, float]:
        _, tip_width = self.resin.key.tip_size()
        h = self.hold_down
        return {
            "frame_wall": self.cottle.frame_wall,
            "plate_below_recess": self.cottle.plate_thickness
            - self.cottle.recess_depth,
            "plate_above_counterbore": self.cottle.plate_thickness
            - self.cottle.recess_depth
            - h.counterbore_depth,
            "lid_thickness": self.cottle.lid_thickness,
            "boss_tip_wall_at_socket": (
                tip_width - self.split.peg_width - self.split.peg_fit
            )
            / 2,
            "funnel_solid_between_pilots": 2 * (h.spot_distance - h.pilot_depth),
        }
