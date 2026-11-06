"""Render actual CAD groupings for editorial review; no exploded placement claims."""

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from efficio import preview, renderer
from efficio.examples.drivetrain import rear_transaxle
from efficio.inspection import inspect_parts
from efficio.objects.assembly import PreviewPart

INK = (30, 43, 59)
MUTED = (82, 98, 117)
BACKGROUND = (241, 245, 249)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("DejaVuSans.ttf", size)


def render(parts: Sequence[PreviewPart], width: int, height: int) -> Image.Image:
    return renderer.create_color_view(
        renderer.tessellate_parts(parts),
        preview.ISOMETRIC,
        style=renderer.PreviewStyle(panel_width=width, panel_height=height, margin=45),
        show_grid=False,
    )


def canvas(title: str, subtitle: str, height: int) -> Image.Image:
    image = Image.new("RGB", (1800, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((50, 28), title, font=font(34), fill=INK)
    draw.text((50, 80), subtitle, font=font(20), fill=MUTED)
    return image


def board(
    path: Path, title: str, cards: List[Tuple[str, str, List[PreviewPart]]]
) -> None:
    rows = (len(cards) + 1) // 2
    image = canvas(
        title,
        "Actual CAD solids | Isometric views, independently scaled | Editorial review",
        140 + rows * 440,
    )
    draw = ImageDraw.Draw(image)
    for i, (name, note, parts) in enumerate(cards):
        x, y = 40 + (i % 2) * 880, 120 + (i // 2) * 440
        image.paste(render(parts, 850, 340), (x, y + 65))
        draw.text((x + 15, y + 4), name, font=font(25), fill=INK)
        draw.text((x + 15, y + 38), note, font=font(17), fill=MUTED)
    image.save(path)


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    assembly = rear_transaxle(crank_angle=30)
    image = canvas(
        "Rear transaxle / physical groupings",
        "Review 01 | Existing geometry and placements retained | No new retention hardware",
        1510,
    )
    image.paste(render(assembly.preview_parts(), 1720, 820), (40, 120))
    draw = ImageDraw.Draw(image)
    draw.text(
        (50, 958),
        "Navigation sections retained; physical groups are nested below",
        font=font(25),
        fill=INK,
    )
    for i, section in enumerate(assembly.children):
        x = 50 + 345 * i
        draw.text((x, 1010), section.name, font=font(24), fill=INK)
        for j, child in enumerate(section.children):
            y = 1055 + j * 40
            draw.rectangle(
                (x, y + 5, x + 17, y + 22), fill=child.resolved_preview_color()
            )
            draw.text((x + 25, y), child.name, font=font(17), fill=INK)
    draw.text(
        (50, 1420),
        "Gearbox support also carries the differential bearings; the differential is not a removable cartridge.",
        font=font(20),
        fill=MUTED,
    )
    draw.text(
        (50, 1455),
        "Bearings and most fasteners remain BOM-only. Colors identify groups; geometry does not prove build readiness.",
        font=font(19),
        fill=MUTED,
    )
    image.save(output / "01-drivetrain-grouping-overview.png")

    def parts(name: str) -> List[PreviewPart]:
        return assembly.find(name).preview_parts()

    board(
        output / "02-transmission-groups.png",
        "Transmission / physical groups",
        [
            (
                "Engine output adapter",
                "Existing crank pinion only; retention is not modeled",
                parts("Engine output adapter"),
            ),
            (
                "Input-shaft assembly",
                "Crown + input pinion + shared shaft",
                parts("Input shaft"),
            ),
            ("Idler-shaft assembly", "Idler gear + its shaft", parts("Idler shaft")),
            (
                "Gearbox support",
                "Two plates + standoffs; carrier bearings listed here",
                parts("Gearbox support"),
            ),
            (
                "Differential carrier",
                "Two carrier halves with integral external ring teeth",
                parts("Carrier"),
            ),
            (
                "Differential internal gears and pins",
                "Suns, paired planets and simplified bolt-shank geometry",
                parts("Internal gears and pins"),
            ),
        ],
    )
    engine = parts("Engine")
    board(
        output / "03-engine-groups.png",
        "Engine / physical groups",
        [
            ("Housing", "Upper block + lower block + head", parts("Housing")),
            (
                "Crankshaft",
                "Webs, crankpins, journals and output stub",
                parts("Crankshaft"),
            ),
            (
                "Piston and rod unit 1",
                "Piston + connecting rod + wrist pin; four units total",
                parts("Piston and rod 1"),
            ),
            ("Flywheel", "Flywheel + flywheel-end stub", parts("Flywheel")),
            (
                "Engine mounts",
                "Existing spacers; installation bolts remain BOM-only",
                parts("Engine mounts"),
            ),
            (
                "Engine / common X section",
                "Inspection cut only; source solids are unchanged",
                inspect_parts(engine, axis="X"),
            ),
        ],
    )
    board(
        output / "04-axle-and-wheel-groups.png",
        "Outputs / separate left and right assemblies",
        [
            (
                "Left axle",
                "Steel half-shaft + pillow block; bearing is BOM-only",
                parts("Left axle"),
            ),
            (
                "Right axle",
                "Steel half-shaft + pillow block; bearing is BOM-only",
                parts("Right axle"),
            ),
            (
                "Left wheel",
                "Hex adapter + rim + tire; retention is BOM-only",
                parts("Left wheel"),
            ),
            (
                "Right wheel",
                "Same part definitions, separate occurrences and quantities",
                parts("Right wheel"),
            ),
        ],
    )
    data = {
        "hierarchy": [
            {
                "path": a.path(),
                "occurrences": [p.label for p in a.instances],
                "hardware": [h.__dict__ for h in a.hardware],
            }
            for a in assembly.walk()
        ],
        "bom_rows": assembly.bom_rows(),
        "bom_totals": assembly.bom_totals(),
    }
    (output / "grouping-review.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Rendered four review boards and hierarchy/BOM data to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("previews/grouping-review")
    )
    main(parser.parse_args().output_dir)
