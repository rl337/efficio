"""Static mold inspection reports: cross-sections and polarity-specific PDFs."""

from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

import cadquery as cq
import reportlab  # type: ignore
from reportlab.lib.pagesizes import letter  # type: ignore
from reportlab.lib.units import inch  # type: ignore
from reportlab.lib.utils import ImageReader  # type: ignore
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics  # type: ignore
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore

from efficio import preview, renderer
from efficio.objects.molds import MoldPolarity, MoldTooling
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape

Axis = Literal["X", "Y", "Z"]
SectionMode = Literal["halfspace", "slab"]


def clone_shape(shape: Shape) -> WorkplaneShape:
    """Return an independent WorkplaneShape with the same solid geometry."""
    if not isinstance(shape, WorkplaneShape):
        raise TypeError(f"Unsupported Shape: {type(shape).__name__}")
    clone = WorkplaneShape(shape._orientation)
    clone._workplane = cq.Workplane(shape._orientation.value).newObject(
        list(shape.workplane().vals())
    )
    return clone


def section_solid(
    shape: Shape,
    axis: Axis = "X",
    position: Union[float, Literal["mid"]] = "mid",
    *,
    mode: SectionMode = "halfspace",
    slab_thickness: float = 2.0,
) -> Shape:
    """Return an inspection solid cut at a plane so internals become outer edges.

    halfspace: keep the negative-side half of the solid (x/y/z <= plane).
    slab: keep only a thin slab centered on the plane.
    """
    if axis not in ("X", "Y", "Z"):
        raise ValueError("axis must be X, Y, or Z")
    if mode not in ("halfspace", "slab"):
        raise ValueError("mode must be halfspace or slab")
    if not math.isfinite(slab_thickness) or slab_thickness <= 0:
        raise ValueError("slab_thickness must be positive and finite")
    bounds = shape.bounds()
    if bounds is None:
        raise ValueError("Cannot section a shape without bounds")
    index = ("X", "Y", "Z").index(axis)
    plane = (
        (bounds[index] + bounds[index + 3]) / 2
        if position == "mid"
        else float(position)
    )
    if not math.isfinite(plane):
        raise ValueError("position must be finite")
    low, high = list(bounds[:3]), list(bounds[3:])
    high[index] = min(
        high[index], plane if mode == "halfspace" else plane + slab_thickness / 2
    )
    if mode == "slab":
        low[index] = max(low[index], plane - slab_thickness / 2)
    result = clone_shape(shape)
    if any(hi <= lo for lo, hi in zip(low, high)):
        result._workplane = cq.Workplane("XY")
        return result
    # Intersect with bounded keep-space, including planes outside the object.
    # Padding only the other axes avoids tolerance slivers at unrelated faces.
    for j in range(3):
        if j != index:
            low[j] -= 1
            high[j] += 1
    sizes = [hi - lo for lo, hi in zip(low, high)]
    center = [(hi + lo) / 2 for lo, hi in zip(low, high)]
    keep = cq.Workplane("XY").box(sizes[0], sizes[1], sizes[2])
    keep = keep.translate((center[0], center[1], center[2]))
    result._workplane = result.workplane().intersect(keep)
    return result


def inspect_parts(
    parts: List[renderer.ColoredSolid],
    *,
    names: Optional[List[str]] = None,
    axis: Optional[Axis] = None,
    position: Union[float, Literal["mid"]] = "mid",
    mode: SectionMode = "halfspace",
    slab_thickness: float = 2.0,
) -> List[renderer.ColoredSolid]:
    """Isolate named components and clip them at one shared world plane.

    Original component names, colors and coordinates are preserved. Midplane
    uses the complete assembly, not each isolated component's bounding box.
    """
    known = {name for name, _, _ in parts}
    if names is not None and set(names) - known:
        raise ValueError(f"Unknown components: {sorted(set(names) - known)}")
    if not parts:
        return []
    plane = position
    if axis is not None and position == "mid":
        box = cq.Compound.makeCompound([solid for _, solid, _ in parts]).BoundingBox()
        i = ("X", "Y", "Z").index(axis)
        plane = (
            (box.xmin, box.ymin, box.zmin)[i] + (box.xmax, box.ymax, box.zmax)[i]
        ) / 2
    output: List[renderer.ColoredSolid] = []
    for name, solid, color in parts:
        if names is not None and name not in names:
            continue
        if axis is None:
            output.append((name, solid, color))
            continue
        shape = WorkplaneShape(Orientation.Front)
        shape._workplane = cq.Workplane("XY").newObject([solid])
        clipped = section_solid(
            shape, axis, plane, mode=mode, slab_thickness=slab_thickness
        )
        for value in clipped.workplane().vals():
            if isinstance(value, cq.Shape) and value.Volume() > 1e-9:
                output.append((name, value, color))
    return output


def _bounds_text(shape: Shape) -> str:
    bounds = shape.bounds()
    if bounds is None:
        return "empty"
    return (
        f"{bounds[3] - bounds[0]:.2f} x "
        f"{bounds[4] - bounds[1]:.2f} x "
        f"{bounds[5] - bounds[2]:.2f} mm"
    )


@dataclass
class InspectionPage:
    """One PDF page: either a rendered shape panel or a text summary."""

    title: str
    caption: str
    shape: Optional[Shape] = None
    parts: Optional[List[renderer.ColoredSolid]] = None
    summary_lines: Optional[List[str]] = None
    views: Optional[Tuple[preview.View, ...]] = None


def _master_shape(tooling: MoldTooling) -> Shape:
    master = tooling.master.shape()
    if master is None:
        raise ValueError("Master produced no geometry")
    return master


def _exploded_assembly(tooling: MoldTooling) -> Shape:
    """Translate master, silicone, and cottle halves into an inspection board."""
    master = clone_shape(_master_shape(tooling))
    silicone = clone_shape(tooling.silicone_shape())
    sections = tooling.cottle_sections()
    if len(sections) < 2:
        raise ValueError("Expected two cottle sections for exploded preview")

    silicone_bounds = silicone.bounds()
    if silicone_bounds is None:
        raise ValueError("Silicone has no bounds")
    span_x = (silicone_bounds[3] - silicone_bounds[0]) * 1.35

    placed_master = master.translate(-span_x * 1.5, 0, 0)
    placed_silicone = silicone.translate(-span_x * 0.25, 0, 0)
    cottle_a = clone_shape(sections[0].geometry).translate(span_x * 0.75, 0, 0)
    cottle_b = clone_shape(sections[1].geometry).translate(span_x * 1.75, 0, 0)

    return placed_master.union(placed_silicone).union(cottle_a).union(cottle_b)


def negative_inspection_pages(tooling: MoldTooling) -> List[InspectionPage]:
    if tooling.polarity is not MoldPolarity.NEGATIVE:
        raise ValueError("negative_inspection_pages requires NEGATIVE polarity")

    master = _master_shape(tooling)
    silicone = tooling.silicone_shape()
    sections = tooling.cottle_sections()

    pages: List[InspectionPage] = [
        InspectionPage(
            title="Inspection summary (NEGATIVE)",
            caption="BOM-style overview of the resin/negative tooling set.",
            summary_lines=[
                f"Polarity: {tooling.polarity.value}",
                f"Purpose: {tooling.purpose.value}",
                f"Printer: {tooling.printer.name}",
                f"Envelope clearance: {tooling.silicone_thickness.value():.2f} mm",
                f"Cottle wall: {tooling.cottle_wall.value():.2f} mm",
                f"Master bounds: {_bounds_text(master)}",
                f"Silicone bounds: {_bounds_text(silicone)}",
                f"Cottle sections: {', '.join(s.name for s in sections)}",
                "Parts: master, silicone negative, cottle A, cottle B",
            ],
        ),
        InspectionPage(
            title="Master",
            caption="Casting master used to form the negative silicone cavity.",
            shape=master,
        ),
        InspectionPage(
            title="Silicone whole",
            caption="Exterior of the negative silicone block (context only).",
            shape=silicone,
        ),
        InspectionPage(
            title="Silicone section X",
            caption="Midplane X cut exposing cavity profile and pour/vent paths.",
            shape=section_solid(silicone, axis="X"),
        ),
        InspectionPage(
            title="Silicone section Z",
            caption="Midplane Z cut exposes cavity; the roof and top openings are removed.",
            shape=section_solid(silicone, axis="Z"),
        ),
    ]

    for section in sections:
        pages.append(
            InspectionPage(
                title=f"Cottle {section.name} whole",
                caption=(
                    f"Functional split={section.split_kind.value}; "
                    "registration and M3 features."
                ),
                shape=section.geometry,
            )
        )
        # Parting is in X; cut in Y to show wall thickness and through-holes.
        pages.append(
            InspectionPage(
                title=f"Cottle {section.name} section Y",
                caption="Half-cut exposes cottle interior; perimeter features remain where present.",
                shape=section_solid(section.geometry, axis="Y"),
            )
        )

    pages.append(
        InspectionPage(
            title="Exploded tooling board",
            caption="Master, silicone, and cottle halves translated for assembly review.",
            shape=_exploded_assembly(tooling),
        )
    )
    return pages


def positive_inspection_pages(tooling: MoldTooling) -> List[InspectionPage]:
    if tooling.polarity is not MoldPolarity.POSITIVE:
        raise ValueError("positive_inspection_pages requires POSITIVE polarity")

    master = _master_shape(tooling)
    silicone = tooling.silicone_shape()
    sections = tooling.cottle_sections()

    pages: List[InspectionPage] = [
        InspectionPage(
            title="Inspection summary (POSITIVE)",
            caption="BOM-style overview of the plaster/positive tooling set.",
            summary_lines=[
                f"Polarity: {tooling.polarity.value}",
                f"Purpose: {tooling.purpose.value}",
                f"Printer: {tooling.printer.name}",
                f"Envelope clearance: {tooling.silicone_thickness.value():.2f} mm",
                f"Cottle wall: {tooling.cottle_wall.value():.2f} mm",
                f"Master bounds: {_bounds_text(master)}",
                f"Silicone bounds: {_bounds_text(silicone)}",
                f"Cottle sections: {', '.join(s.name for s in sections)}",
                "Parts: master witness, silicone positive replica, cottle A, cottle B",
                "Clearance around the positive is plaster volume, not silicone thickness.",
            ],
        ),
        InspectionPage(
            title="Master witness",
            caption="Exterior master used to define the positive silicone replica.",
            shape=master,
        ),
        InspectionPage(
            title="Silicone whole",
            caption="Positive silicone replica preserves the master profile.",
            shape=silicone,
        ),
        InspectionPage(
            title="Silicone section X",
            caption="Midplane X cut through the silicone positive replica.",
            shape=section_solid(silicone, axis="X"),
        ),
        InspectionPage(
            title="Silicone section Y",
            caption="Midplane Y cut through the silicone positive replica.",
            shape=section_solid(silicone, axis="Y"),
        ),
        InspectionPage(
            title="Master witness comparison",
            caption="Witness panel: master alone for comparison with the sectioned envelope.",
            shape=master,
        ),
    ]

    for section in sections:
        pages.append(
            InspectionPage(
                title=f"Cottle {section.name} whole",
                caption=(
                    f"Functional split={section.split_kind.value}; "
                    "registration and M3 features."
                ),
                shape=section.geometry,
            )
        )
        pages.append(
            InspectionPage(
                title=f"Cottle {section.name} section Y",
                caption="Half-cut exposes cottle interior; perimeter features remain where present.",
                shape=section_solid(section.geometry, axis="Y"),
            )
        )

    pages.append(
        InspectionPage(
            title="Exploded tooling board",
            caption="Master, silicone, and cottle halves translated for assembly review.",
            shape=_exploded_assembly(tooling),
        )
    )
    return pages


def inspection_pages_for(tooling: MoldTooling) -> List[InspectionPage]:
    if tooling.polarity is MoldPolarity.NEGATIVE:
        pages = negative_inspection_pages(tooling)
    elif tooling.polarity is MoldPolarity.POSITIVE:
        pages = positive_inspection_pages(tooling)
    else:
        raise ValueError(f"Unsupported polarity: {tooling.polarity}")
    sections = tooling.cottle_sections()
    components = [("Silicone", tooling.silicone_shape(), (91, 169, 191))] + [
        (f"Cottle {part.name}", part.geometry, (225, 156, 75)) for part in sections
    ]
    parts: List[renderer.ColoredSolid] = [
        (name, value, color)
        for name, shape, color in components
        for value in shape.workplane().vals()
        if isinstance(value, cq.Shape)
    ]
    for page in pages:
        if page.shape is not None:
            color = (91, 169, 191) if "Silicone" in page.title else (225, 156, 75)
            page.parts = [
                (page.title, value, color)
                for value in page.shape.workplane().vals()
                if isinstance(value, cq.Shape)
            ]
    for page in pages:
        if page.title == "Exploded tooling board":
            board: List[renderer.ColoredSolid] = []
            cursor = 0.0
            for name, shape, color in [
                ("Master", _master_shape(tooling), (155, 160, 170))
            ] + components:
                bounds = shape.bounds()
                assert bounds is not None
                shift = cursor - bounds[0]
                board.extend(
                    (name, value.translate((shift, 0, 0)), color)
                    for value in shape.workplane().vals()
                    if isinstance(value, cq.Shape)
                )
                cursor += bounds[3] - bounds[0] + 15
            page.parts = board
            board_shape = WorkplaneShape(Orientation.Front)
            board_shape._workplane = cq.Workplane("XY").newObject(
                [cq.Compound.makeCompound([solid for _, solid, _ in board])]
            )
            page.shape = board_shape
            page.caption = (
                "Separated source solids; master gray, silicone blue, cottle amber."
            )
    pages.append(
        InspectionPage(
            "Assembled tooling, common Y cut",
            "All components clipped at the same world plane; silicone blue, cottle amber. "
            "Contact and unintended overlap require solid intersection checks, not color alone.",
            parts=inspect_parts(parts, axis="Y"),
        )
    )
    pages.append(
        InspectionPage(
            "Manufacturing steps and limitations",
            "Inspection geometry is not a validated casting process or print release.",
            summary_lines=[
                "1. Print and finish the master; verify dimensions, surface finish and release compatibility.",
                "2. Print, assemble and leak-test the containment and support parts before pouring.",
                "3. Negative: establish master suspension, parting, keys and a safe demolding path; pour and cure silicone.",
                "4. Positive: master -> negative production mold -> positive silicone -> negative plaster mold -> hollow slip-cast vessel. The silicone production mold is not supplied.",
                "5. Plaster: design segmented molds, parting barriers, suspension fixtures, an exposed neck fill/drain opening and release sequence before pouring. These are not generated.",
                "6. Verify fastener length, access, tolerances, material shrinkage and vent flow on physical prototypes.",
                "7. Oversize parts need manufacturing splits and joints. Printer fit is only an axis-aligned bounds test, not printability proof.",
                "8. Slip casting needs porous plaster to remove water. The flask master is solid, not a hollow finished vessel. Wall thickness and drying/firing shrinkage require trials.",
                "9. Silicone is unsplit; plan a cut mold or staged pour. Master suspension and silicone charging fixtures are not generated. Verify every local high point is vented.",
                "10. Print fit coupons; seal seams and fastener penetrations. Leak tightness, clamp strength, release agents, cure inhibition and material shrinkage are not qualified.",
            ],
        )
    )
    for page in pages:
        if "section Y" in page.title or "common Y cut" in page.title:
            page.views = (
                preview.TOP,
                preview.FRONT,
                preview.View("CUT FACE (+Y)", (0, 1, 0), (0, 0, 1)),
                preview.View("CUT ISOMETRIC", (1, 1.2, 0.9), (0, 0, 1)),
            )
    return pages


def _register_fonts() -> None:
    directory = Path(reportlab.__file__).parent / "fonts"
    for name, file in (("Inspection", "Vera.ttf"), ("Inspection-Bold", "VeraBd.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(directory / file)))


def _text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    size: int = 11,
    bold: bool = False,
) -> float:
    font = "Inspection-Bold" if bold else "Inspection"
    pdf.setFont(font, size)
    for line in simpleSplit(text, font, size, width):
        pdf.drawString(x, y, line)
        y -= size * 1.4
    return y


def _draw_page(
    pdf: canvas.Canvas,
    page: InspectionPage,
    page_size: Tuple[float, float],
    number: int,
    total: int,
) -> None:
    width, height = page_size
    margin = 0.6 * inch
    y = _text(pdf, page.title, margin, height - margin, width - 2 * margin, 16, True)
    y = _text(pdf, page.caption, margin, y - 12, width - 2 * margin)
    if page.shape is not None:
        y = _text(
            pdf,
            f"Bounds: {_bounds_text(page.shape)}",
            margin,
            y - 8,
            width - 2 * margin,
            10,
        )
    if page.summary_lines is not None:
        for line in page.summary_lines:
            y = _text(pdf, line, margin, y - 14, width - 2 * margin)
            if y < 50:
                raise ValueError("Summary exceeds page; split into additional pages")
    else:
        if page.parts is not None:
            image = renderer.create_color_composite_image(
                page.parts, annotate=False, views=page.views or preview.STANDARD_VIEWS
            )
        elif page.shape is not None:
            image = renderer.create_color_composite_image(
                [
                    (page.title, value, (91, 169, 191))
                    for value in page.shape.workplane().vals()
                    if isinstance(value, cq.Shape)
                ],
                annotate=False,
            )
        else:
            raise ValueError(f"Page missing geometry: {page.title}")
        y = _text(
            pdf,
            (
                "Views: top (+Z), front (+X), cut face (+Y), cut isometric."
                if page.views is not None
                else "Views: top (+Z), front (+X), left side (-Y), isometric."
            ),
            margin,
            y - 10,
            width - 2 * margin,
            10,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        scale = min((width - 2 * margin) / image.width, (y - 60) / image.height)
        draw_w, draw_h = image.width * scale, image.height * scale
        pdf.drawImage(
            ImageReader(buffer),
            (width - draw_w) / 2,
            y - draw_h - 10,
            width=draw_w,
            height=draw_h,
            mask="auto",
        )
    _text(
        pdf,
        f"{number} / {total}  |  Geometry inspection, not a manufacturing release",
        margin,
        26,
        width - 2 * margin,
        9,
    )
    pdf.showPage()


def write_mold_inspection_pdf(tooling: MoldTooling, path: str) -> str:
    """Write a polarity-specific multi-page inspection PDF; return path."""
    pages = inspection_pages_for(tooling)
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    page_size = letter
    _register_fonts()
    pdf = canvas.Canvas(path, pagesize=page_size)
    for number, page in enumerate(pages, 1):
        _draw_page(pdf, page, page_size, number, len(pages))
    pdf.save()
    return path


def generate_example_inspection_pdfs(output_dir: str) -> List[str]:
    """Generate resin and plaster inspection PDFs into output_dir."""
    from efficio.examples.mold_tooling import plaster_triangular_flask_tooling
    from efficio.measures import Millimeter
    from efficio.objects.gears import SpurGear

    gear = SpurGear.from_tip_radius(
        Millimeter(30), 20, Millimeter(8), lightening_holes=6, engrave_identity=False
    )
    resin = MoldTooling(gear, MoldPolarity.NEGATIVE)

    os.makedirs(output_dir, exist_ok=True)
    outputs = [
        (
            resin,
            os.path.join(output_dir, "resin_gear_inspection.pdf"),
        ),
        (
            plaster_triangular_flask_tooling(),
            os.path.join(output_dir, "plaster_vase_inspection.pdf"),
        ),
    ]
    written: List[str] = []
    for tooling, path in outputs:
        written.append(write_mold_inspection_pdf(tooling, path))
    return written


def main(argv: Optional[List[str]] = None) -> int:
    """CLI: write example mold inspection PDFs (Docker-friendly)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate polarity-specific mold inspection PDFs."
    )
    parser.add_argument(
        "--output-dir",
        default="previews",
        help="Directory for resin_gear_inspection.pdf and plaster_vase_inspection.pdf",
    )
    args = parser.parse_args(argv)
    for path in generate_example_inspection_pdfs(args.output_dir):
        sys.stdout.write(f"{path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
