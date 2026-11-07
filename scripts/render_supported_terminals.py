"""Before/after and section review of actual supported hose-terminal CAD."""

import argparse
import json
from pathlib import Path

from PIL import ImageDraw
from render_drivetrain_groups import INK, canvas, font
from render_resin_engine import render
from render_water_feature_pump import main as export_pump

from efficio import preview, renderer
from efficio.examples.water_feature_pump import (
    water_feature_pump,
    water_pump_dimensions,
)
from efficio.inspection import inspect_parts
from efficio.objects.connectors import CommonHoseSize


def main(output: Path) -> None:
    export_pump(output)
    before = water_feature_pump(supported_roots=False).preview_parts()
    after = water_feature_pump().preview_parts()
    image = canvas(
        "Hose terminals / broader smooth roots",
        "Actual Efficio CAD | Previous straight roots (left) / supported roots (right) | Strength remains untested",
        1400,
    )
    image.paste(render(before, 840, 850), (40, 140))
    image.paste(render(after, 840, 850), (920, 140))
    draw = ImageDraw.Draw(image)
    lines = [
        "Revolved smooth flare: 13 mm base diameter blending to the 8 mm stem over 8 mm.",
        "Upper relief keeps added support 0.05 mm below the cover joint; gasket and cover remain removable.",
        "4 mm bore, 8.8 mm barb peaks, 5 mm clamp land and 17 mm target hose engagement are unchanged.",
        "Root ends 1 mm before the hose target position. Hose and clamp access checks pass.",
        "This adds material around the joint; it is not a measured strength improvement or a pressure rating.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 1030 + i * 50), line, font=font(21), fill=INK)
    image.save(output / "25-supported-terminal-comparison.png")
    d = water_pump_dimensions()
    cut = inspect_parts(
        after, axis="X", position=d.pump.centres / 2 + 0.05, mode="halfspace"
    )
    image = canvas(
        "Supported terminal / section and nominal hose sizes",
        "Display section near the port centerline | Explicit hose IDs; barb crests are separately parameterized",
        1400,
    )
    picture = renderer.create_color_view(
        renderer.tessellate_parts(cut),
        preview.View("YZ", (1, 0, 0), (0, 0, 1)),
        style=renderer.PreviewStyle(panel_width=1720, panel_height=750, margin=50),
        show_grid=False,
    )
    image.paste(picture, (40, 140))
    draw = ImageDraw.Draw(image)
    lines = [
        "Default water pump: 8 mm hose ID / provisional 12 mm OD. Minimum terminal wall stays 2 mm.",
        "Metric IDs: 4, 6, 8, 10, 12 mm. Imperial IDs: 1/8, 3/16, 1/4, 5/16, 3/8, 1/2 inch.",
        "3/16 inch = 4.7625 mm, not 4 mm. 5/16 inch = 7.9375 mm, not 8 mm.",
        "Aquarium presets: Danner nominal 3/16-inch ID; Tetra AH 4 mm ID / 6 mm OD. They are distinct.",
        "Airline presets do not establish Tetra Whisper barb dimensions or water-pump suitability.",
        "Small IDs fail this pump's bore/wall budget. Larger IDs may need lower ports or a different chamber.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 940 + i * 55), line, font=font(21), fill=INK)
    image.save(output / "26-supported-terminal-section.png")
    old = next(s for n, s, _ in before if n == "water_body")
    new = next(s for n, s, _ in after if n == "water_body")
    measurements = {
        "old_body_mm3": old.Volume(),
        "supported_body_mm3": new.Volume(),
        "added_root_material_mm3": new.cut(old).Volume(),
        "removed_material_mm3": old.cut(new).Volume(),
        "sizes": [
            {
                "name": s.name,
                "id_mm": s.value.id_mm,
                "od_mm": s.value.od_mm,
                "source": s.value.source,
            }
            for s in CommonHoseSize
        ],
    }
    (output / "supported-root-measurements.json").write_text(
        json.dumps(measurements, indent=2)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
