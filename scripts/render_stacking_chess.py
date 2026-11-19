"""Preview boards for the keyed resin cylinders, masters and cottle.

Uses efficio's own renderer: ``renderer.create_object_preview`` for single
objects and ``renderer.create_color_composite_image`` for composed scenes.
"""

import argparse
from pathlib import Path
from typing import List, Tuple

import cadquery as cq
from PIL import Image

from efficio import renderer
from efficio.examples.stacking_chess import stacking_chess_set
from efficio.objects.base import Color
from efficio.objects.games.chess import (
    ResinMasterAssembly,
    ResinMoldPlan,
    ResinMoldSetup,
    ResinPieceCast,
)
from efficio.objects.games.chess import resin_mold as rm
from efficio.objects.games.chess.resin_mold import shape_of

PIECE_COLORS: List[Color] = [
    (210, 90, 80),
    (90, 140, 210),
    (95, 180, 110),
    (225, 175, 70),
    (160, 110, 200),
    (80, 190, 190),
]


def save(image: Image.Image, output_dir: Path, name: str) -> None:
    path = output_dir / f"{name}.png"
    image.save(path, "PNG")
    print(f"wrote {path}")


def piece_set(output_dir: Path) -> None:
    parts, legend = [], []
    x = 0.0
    for entry, color in zip(stacking_chess_set(), PIECE_COLORS):
        solid = shape_of(entry.piece.solid().translate((x, 0, 0)))
        parts.append((entry.name, solid, color))
        legend.append((f"{entry.name} x{entry.quantity}", color))
        x += 38.0
    save(renderer.create_color_composite_image(parts, legend=legend), output_dir, "set")


def piece_casts(output_dir: Path) -> None:
    for entry in stacking_chess_set():
        cast = ResinPieceCast(entry.piece)
        save(renderer.create_object_preview(cast), output_dir, f"cast_{entry.name}")


def key_stack(output_dir: Path) -> None:
    """Two cylinders stacked aligned, opened along y = 0."""
    plan = ResinMoldPlan()
    body = rm.cast_body(plan)
    opening = rm._half_space(upper=False)
    lower = shape_of(body.cut(opening))
    upper = shape_of(body.translate((0, 0, plan.body_height)).cut(opening))
    parts = [("lower", lower, (150, 200, 230)), ("upper", upper, (235, 190, 120))]
    legend = [
        ("lower cylinder (boss up)", parts[0][2]),
        ("upper (notch down)", parts[1][2]),
    ]
    save(
        renderer.create_color_composite_image(parts, legend=legend),
        output_dir,
        "key_stack",
    )


def master_parts(output_dir: Path) -> None:
    save(
        renderer.create_object_preview(ResinMasterAssembly()),
        output_dir,
        "master_parts",
    )


def exploded_master(output_dir: Path) -> None:
    plan = ResinMoldPlan()
    spacer_z, top_z, funnel_z = rm._master_offsets(plan)
    gap = 14.0
    placed = [
        ("bottom cap", rm.master_bottom_cap(plan), 0.0),
        ("spacer", rm.master_spacer(plan), spacer_z + gap),
        ("top cap", rm.master_top_cap(plan), top_z + 2 * gap),
        ("funnel", rm.master_funnel(plan), funnel_z + 3 * gap),
    ]
    colors = ResinMasterAssembly.PART_COLORS
    parts = [
        (name, shape_of(wp.translate((0, 0, z))), color)
        for (name, wp, z), color in zip(placed, colors)
    ]
    legend = [(name, color) for (name, _, _), color in zip(placed, colors)]
    save(
        renderer.create_color_composite_image(parts, legend=legend),
        output_dir,
        "master_exploded",
    )


def pour_setups(output_dir: Path) -> None:
    for pour in ("A", "B"):
        setup = ResinMoldSetup(ResinMoldPlan(), pour)
        save(renderer.create_object_preview(setup), output_dir, f"pour_{pour.lower()}")


def hold_down_closeup(output_dir: Path) -> None:
    """Funnel end of pour A: screw, pilot, spot face and plate counterbore."""
    plan = ResinMoldPlan()
    window = (
        cq.Workplane("XY")
        .box(24.0, 80.0, 90.0)
        .translate((plan.master_length - 12.0, 0, -14.0))
    )
    setup = ResinMoldSetup(plan, "A", section_y=plan.hold_down.offset)
    parts: List[Tuple[str, cq.Shape, Color]] = []
    for name, solid, color in setup.preview_parts((0, 0, 0)):
        trimmed = cq.Workplane("XY").newObject([solid]).intersect(window)
        if shape_of(trimmed).Volume() > 1e-6:
            parts.append((name, shape_of(trimmed), color))
    legend = setup.preview_legend((0, 0, 0))
    save(
        renderer.create_color_composite_image(parts, legend=legend),
        output_dir,
        "hold_down",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="previews/stacking-chess")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for step in (
        piece_set,
        piece_casts,
        key_stack,
        master_parts,
        exploded_master,
        pour_setups,
        hold_down_closeup,
    ):
        step(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
