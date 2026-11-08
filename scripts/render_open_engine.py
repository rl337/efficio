"""Render a measured before/after proposal from the actual toy-engine CAD."""

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import List

from PIL import ImageDraw
from render_drivetrain_groups import INK, MUTED, board, canvas, font

from efficio import preview, renderer
from efficio.examples.drivetrain import engine_assembly, rear_transaxle
from efficio.examples.open_engine import demonstration_layout
from efficio.objects.assembly import PreviewPart
from efficio.objects.powertrain.layout import DrivetrainLayout


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    proposal = demonstration_layout()
    e = proposal.engine
    original = DrivetrainLayout().engine
    old = engine_assembly(crank_angle=30)
    full = rear_transaxle(proposal, 30)
    new = full.find("Engine")
    larger_closed = engine_assembly(
        DrivetrainLayout(engine=replace(proposal.engine, windowed_block=False)), 30
    )
    names = ("engine_block_upper", "engine_block_lower", "cylinder_head")

    volumes = {
        title: {n: a.instance(n).solid.Volume() for n in names}
        for title, a in [
            ("original", old),
            ("larger_closed", larger_closed),
            ("proposal", new),
        ]
    }
    totals = {k: sum(v.values()) for k, v in volumes.items()}
    saved = 100 * (1 - totals["proposal"] / totals["larger_closed"])
    change = 100 * (totals["proposal"] / totals["original"] - 1)
    board(
        output / "05-open-engine-before-after.png",
        "Larger inline-four / windowed toy-engine proposal",
        [
            (
                f"Before: enclosed {original.bore:g} mm bore",
                f"{original.stroke:g} mm stroke | {original.cylinder_spacing:g} mm pitch | {original.block_length:g} mm block length",
                old.preview_parts(),
            ),
            (
                f"Proposal: open {e.bore:g} mm bore",
                f"{e.stroke:g} mm stroke | {e.cylinder_spacing:g} mm pitch | {e.block_length:g} mm block length",
                new.preview_parts(),
            ),
            (
                "Windowed housing and open head",
                f"Volume: {saved:.1f}% below larger closed housing; {change:+.1f}% vs original",
                new.find("Housing").preview_parts(),
            ),
            (
                "Proposal in the drivetrain",
                "Existing physical groups retained; dimensions adapt to engine",
                full.preview_parts(),
            ),
        ],
    )
    image = canvas(
        "Visible piston motion / editorial review",
        "Actual CAD | Side view at two crank angles, independently fitted | No display cutaway",
        1200,
    )
    draw = ImageDraw.Draw(image)
    for index, angle in enumerate((30.0, 90.0)):
        engine = new if angle == 30 else engine_assembly(proposal, angle)
        # Hide flywheel and installation spacers only for this labelled inspection view.
        parts: List[PreviewPart] = [
            p
            for p in engine.preview_parts()
            if p[0] != "flywheel" and not p[0].startswith("engine_mount")
        ]
        panel = renderer.create_color_view(
            renderer.tessellate_parts(parts),
            preview.SIDE,
            style=renderer.PreviewStyle(panel_width=1700, panel_height=425, margin=35),
            show_grid=False,
        )
        y = 150 + index * 465
        draw.text(
            (50, y - 35),
            f"Crank angle {angle:g} degrees — flywheel and mounting spacers hidden",
            font=font(23),
            fill=INK,
        )
        image.paste(panel, (50, y))
    draw.text(
        (50, 1095),
        f"End walls, bearing seats, {e.frame_rail:g} mm rails and {e.mount_bridge_height:g} mm mounting bridges retained.",
        font=font(22),
        fill=INK,
    )
    draw.text(
        (50, 1135),
        "Open guide arcs need physical wear/stiffness testing. No sealing, combustion or strength claim.",
        font=font(20),
        fill=MUTED,
    )
    image.save(output / "06-open-engine-piston-views.png")
    data = {
        "dimensions_mm": {
            "bore": e.bore,
            "stroke": e.stroke,
            "pitch": e.cylinder_spacing,
            "block_length": e.block_length,
            "window_width": e.bore * e.window_width_fraction,
            "frame_rail": e.frame_rail,
            "mount_bridge_height": e.mount_bridge_height,
        },
        "housing_solid_volumes_mm3": volumes,
        "housing_totals_mm3": totals,
        "reduction_vs_same_size_closed_percent": saved,
        "change_vs_original_housing_percent": change,
        "layout_problems": proposal.problems(),
        "notes": "CAD solid volume, not slicer material usage; no structural optimization or physical validation.",
    }
    (output / "open-engine-measurements.json").write_text(
        json.dumps(data, indent=2) + "\n"
    )
    print(json.dumps(data, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("previews/open-engine"))
    main(parser.parse_args().output_dir)
