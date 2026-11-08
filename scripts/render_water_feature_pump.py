"""Render and export the standalone wet-end review from actual Efficio solids."""

import argparse
import json
from pathlib import Path

import cadquery as cq
from PIL import ImageDraw
from render_drivetrain_groups import INK, canvas, font
from render_resin_engine import render

from efficio import preview, renderer
from efficio.examples.water_feature_pump import (
    water_feature_pump,
    water_hose_terminal,
    water_pump_dimensions,
)
from efficio.inspection import inspect_parts
from efficio.objects.connectors import HoseBarb
from efficio.objects.pumps.blind_support import (
    BlindSupportPart,
    measured_housing_interfaces,
)
from efficio.objects.pumps.external_gear import GearPumpGeometry


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    d = water_pump_dimensions()
    g = d.pump
    (output / "wall-measurements.json").write_text(
        json.dumps(
            {
                "analytical_mm": d.wall_measurements(),
                "cad_section_mm": measured_housing_interfaces(d),
            },
            indent=2,
        )
    )
    assembly = water_feature_pump()
    parts = assembly.preview_parts()
    for name, solid, _ in parts:
        cq.exporters.export(solid, str(output / (name + ".step")))
    image = canvas(
        "Water-feature pump / integral tube terminals",
        "Actual Efficio CAD | Two integral hose barbs | Provisional 8 mm ID hose | No measured sealing or pumping",
        1400,
    )
    image.paste(render(parts, 840, 850), (40, 140))
    exploded = []
    for name, solid, color in parts:
        offset = 28 if name == "water_cover" else 14 if name == "water_gasket" else 0
        exploded.append((name, solid.translate((0, 0, offset)), color))
    image.paste(render(exploded, 840, 850), (920, 140))
    draw = ImageDraw.Draw(image)
    lines = [
        "Left: assembled case. Right: cover and compressed gasket envelope lifted for review.",
        "16T + 16T shared involute rotors; module 1.25; 8 mm width; 20 mm shaft spacing.",
        "Two 4 mm through bores; 8 mm stems; 8.8 mm barb peaks; 5 mm straight clamp lands.",
        "One 6 mm nominal driver exits the cover. Idler and rear driver journals end in blind pockets.",
        "12 x 4 mm seal seat is EMPTY; seal, dry coupling, axial retention and clamp hardware must be selected.",
        "Hose engagement: 17 mm. Overall terminal-to-terminal span: 76 mm. Hoses and clamps are not installed.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 1020 + i * 48), line, font=font(21), fill=INK)
    image.save(output / "23-pump-hose-terminals.png")
    # Display plane slightly off port-axis seams avoids an OCC coincident-edge failure.
    face = inspect_parts(
        [p for p in parts if p[0] == "water_body"],
        axis="Z",
        position=g.port(1)[2] + 0.05,
        mode="halfspace",
    )
    face += [p for p in parts if p[0] in {"driver", "idler"}]
    fluid_g = GearPumpGeometry(**vars(g))
    terminal = HoseBarb(water_hose_terminal(d))
    body_object = BlindSupportPart(d, "body", terminal.dimensions, 12)
    fluid = fluid_g.cavity().fuse(
        fluid_g.port_void(-1),
        fluid_g.port_void(1),
        *(body_object.place_terminal(terminal.bore(), sign) for sign in (-1, 1)),
    )
    fluid = fluid.intersect(
        cq.Solid.makeBox(200, 200, g.base + g.width / 2, cq.Vector(-100, -100, 0))
    )
    # Clip drilling cutters to the actual side envelope: no fictitious external tubes.
    envelope = cq.Solid.makeCylinder(g.radius + d.exterior_offset, g.depth).fuse(
        cq.Solid.makeCylinder(
            g.radius + d.exterior_offset, g.depth, cq.Vector(g.centres, 0, 0)
        )
    )
    envelope = envelope.fuse(
        *(body_object.place_terminal(terminal.envelope(), sign) for sign in (-1, 1))
    )
    fluid = fluid.intersect(envelope)
    face.append(("actual_chamber_and_port_void", fluid, (217, 235, 241)))
    axial = inspect_parts(parts, axis="Y", position=0, mode="halfspace")
    image = canvas(
        "Tube terminals / continuous passages and hose access",
        "Display sections only: manufactured housing stays whole | Rotation viewed from the drive end (+Z)",
        1400,
    )
    for section, view, x in [
        (face, preview.View("face", (0, 0, 1), (0, 1, 0)), 40),
        (axial, preview.View("axial", (0, 1, 0), (0, 0, 1)), 920),
    ]:
        picture = renderer.create_color_view(
            renderer.tessellate_parts(section),
            view,
            style=renderer.PreviewStyle(panel_width=840, panel_height=850, margin=60),
            show_grid=False,
        )
        image.paste(picture, (x, 140))
    draw = ImageDraw.Draw(image)
    lines = [
        "Face (left): upper port INLET with left driver CCW / right idler CW; lower port OUTLET.",
        "Fluid is carried around both outer walls. Reverse rotation reverses the ports.",
        "Axial section (right): blind rear journals and idler cover pocket; only driver reaches the exterior.",
        "Terminal minimum radial wall: 2 mm. Port axes lowered 0.3 mm: 2.08 mm remains below the gasket groove.",
        "Leaks remain possible through running gaps, pinned rotor bores, gasket and unfilled shaft-seal seat.",
        "Retention needs a qualified hose/clamp pair and pull-off/leak tests; integral resin barbs are not pressure-rated.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 1020 + i * 48), line, font=font(21), fill=INK)
    image.save(output / "24-pump-terminal-passages.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
