"""Keyed resin cylinders, modular masters and printed cottles for the chess set.

For each piece type the kit holds the printed master parts (bottom cap, spacer,
top cap, funnel), the cottle (frame, plate, lid, parting blocks A and B) and the
silicone to mix per half.  Every printed part is checked against the printer's
build volume before it is exported.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import cadquery as cq

from efficio.examples.stacking_chess import SetEntry, stacking_chess_set
from efficio.machines import PRUSA_MK4, MachineProfile
from efficio.objects.games.chess.resin_geometry import ResinMoldPlan
from efficio.objects.games.chess.resin_mold import (
    ResinMasterBottomCap,
    ResinMasterFunnel,
    ResinMasterSpacer,
    ResinMasterTopCap,
    ResinMoldBlockA,
    ResinMoldBlockB,
    ResinMoldFrame,
    ResinMoldLid,
    ResinMoldPlate,
    shape_of,
    silicone_per_half_ml,
)
from efficio.objects.profiles import wrap

SILICONE_MARGIN = 1.10  # mix this much extra per half


@dataclass(frozen=True)
class PrintedPart:
    name: str
    solid: cq.Workplane

    def dimensions(self) -> Tuple[float, float, float]:
        box = shape_of(self.solid).BoundingBox()
        return (box.xlen, box.ylen, box.zlen)


@dataclass(frozen=True)
class MoldKit:
    piece: str
    plan: ResinMoldPlan
    parts: Tuple[PrintedPart, ...]
    silicone_ml: float  # per half, before the margin

    @property
    def silicone_to_mix_ml(self) -> float:
        return self.silicone_ml * SILICONE_MARGIN

    def oversize(self, machine: MachineProfile = PRUSA_MK4) -> List[str]:
        return [
            f"{self.piece}/{p.name}: {p.dimensions()} exceeds {machine.name}"
            for p in self.parts
            if not machine.build_volume.fits(p.dimensions())
        ]


def mold_kit(entry: SetEntry) -> MoldKit:
    height = shape_of(entry.piece.solid()).BoundingBox().zmax
    plan = ResinMoldPlan(
        piece_height=height, piece_base_radius=entry.piece.body.base_radius
    )
    parts = (
        PrintedPart("master_bottom_cap", ResinMasterBottomCap(plan).solid()),
        PrintedPart("master_spacer", ResinMasterSpacer(plan).solid()),
        PrintedPart("master_top_cap", ResinMasterTopCap(plan).solid()),
        PrintedPart("master_funnel", ResinMasterFunnel(plan).print_solid()),
        PrintedPart("cottle_frame", ResinMoldFrame(plan).solid()),
        PrintedPart("cottle_plate", ResinMoldPlate(plan).solid()),
        PrintedPart("cottle_lid", ResinMoldLid(plan).solid()),
        PrintedPart("cottle_block_a", ResinMoldBlockA(plan).solid()),
        PrintedPart("cottle_block_b", ResinMoldBlockB(plan).solid()),
    )
    return MoldKit(entry.name, plan, parts, silicone_per_half_ml(plan))


def stacking_chess_mold_kits() -> List[MoldKit]:
    return [mold_kit(entry) for entry in stacking_chess_set()]


def export_stacking_chess_mold_stls(
    directory: str, machine: MachineProfile = PRUSA_MK4
) -> Dict[str, List[str]]:
    """Write every printed part as ``<piece>/<part>.stl``; refuse oversize parts."""
    kits = stacking_chess_mold_kits()
    oversize = [problem for kit in kits for problem in kit.oversize(machine)]
    if oversize:
        raise ValueError("; ".join(oversize))
    written: Dict[str, List[str]] = {}
    for kit in kits:
        folder = os.path.join(directory, kit.piece)
        os.makedirs(folder, exist_ok=True)
        written[kit.piece] = []
        for part in kit.parts:
            path = os.path.join(folder, f"{part.name}.stl")
            wrap(part.solid).as_stl_file(path)
            written[kit.piece].append(path)
    return written
