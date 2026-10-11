"""Static mold inspection reports: cross-sections and polarity-specific PDFs."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple, Union

import cadquery as cq
from reportlab.lib.pagesizes import letter  # type: ignore
from reportlab.lib.units import inch  # type: ignore
from reportlab.lib.utils import ImageReader  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore

from efficio import renderer
from efficio.objects.mold_tooling import MoldPolarity, MoldTooling
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape, new_shape

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
    bounds = shape.bounds()
    if bounds is None:
        raise ValueError("Cannot section a shape without bounds")

    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    center = (
        (min_x + max_x) / 2,
        (min_y + max_y) / 2,
        (min_z + max_z) / 2,
    )
    sizes = (max_x - min_x, max_y - min_y, max_z - min_z)
    if position == "mid":
        plane = {"X": center[0], "Y": center[1], "Z": center[2]}[axis]
    else:
        plane = float(position)

    pad = max(sizes) * 2 + 20.0
    result = clone_shape(shape)

    if mode == "halfspace":
        # Remove the positive half so the cut face exposes the interior.
        if axis == "X":
            cutter = (
                new_shape(Orientation.Front)
                .box(pad, pad, pad)
                .translate(plane + pad / 2, center[1], center[2])
            )
        elif axis == "Y":
            cutter = (
                new_shape(Orientation.Front)
                .box(pad, pad, pad)
                .translate(center[0], plane + pad / 2, center[2])
            )
        else:
            cutter = (
                new_shape(Orientation.Front)
                .box(pad, pad, pad)
                .translate(center[0], center[1], plane + pad / 2)
            )
        return result.cut(cutter)

    # Slab mode: remove material outside a band around the plane.
    half = slab_thickness / 2
    if axis == "X":
        low = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(plane - half - pad / 2, center[1], center[2])
        )
        high = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(plane + half + pad / 2, center[1], center[2])
        )
    elif axis == "Y":
        low = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(center[0], plane - half - pad / 2, center[2])
        )
        high = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(center[0], plane + half + pad / 2, center[2])
        )
    else:
        low = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(center[0], center[1], plane - half - pad / 2)
        )
        high = (
            new_shape(Orientation.Front)
            .box(pad, pad, pad)
            .translate(center[0], center[1], plane + half + pad / 2)
        )
    return result.cut(low).cut(high)


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
    summary_lines: Optional[List[str]] = None


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
                f"Silicone thickness: {tooling.silicone_thickness.value():.2f} mm",
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
            caption="Midplane Z cut exposing cavity and top pour openings.",
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
                caption="Section through cottle wall, fasteners, and registration.",
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
                f"Silicone thickness: {tooling.silicone_thickness.value():.2f} mm",
                f"Cottle wall: {tooling.cottle_wall.value():.2f} mm",
                f"Master bounds: {_bounds_text(master)}",
                f"Silicone bounds: {_bounds_text(silicone)}",
                f"Cottle sections: {', '.join(s.name for s in sections)}",
                "Parts: master witness, silicone positive envelope, cottle A, cottle B",
            ],
        ),
        InspectionPage(
            title="Master witness",
            caption="Required witness of the embedded master geometry.",
            shape=master,
        ),
        InspectionPage(
            title="Silicone whole",
            caption="Positive silicone envelope exterior (often brick-like).",
            shape=silicone,
        ),
        InspectionPage(
            title="Silicone section X",
            caption="Midplane X cut; embedded master silhouette should appear inside.",
            shape=section_solid(silicone, axis="X"),
        ),
        InspectionPage(
            title="Silicone section Y",
            caption="Midplane Y cut through the positive envelope and master.",
            shape=section_solid(silicone, axis="Y"),
        ),
        InspectionPage(
            title="Master beside silicone section",
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
                caption="Section through cottle wall, fasteners, and registration.",
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
        return negative_inspection_pages(tooling)
    if tooling.polarity is MoldPolarity.POSITIVE:
        return positive_inspection_pages(tooling)
    raise ValueError(f"Unsupported polarity: {tooling.polarity}")


def _draw_summary_page(
    pdf: canvas.Canvas,
    page: InspectionPage,
    page_size: Tuple[float, float],
) -> None:
    width, height = page_size
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(0.75 * inch, height - 0.75 * inch, page.title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(0.75 * inch, height - 1.05 * inch, page.caption)
    y = height - 1.5 * inch
    pdf.setFont("Helvetica", 11)
    for line in page.summary_lines or []:
        pdf.drawString(0.9 * inch, y, line)
        y -= 0.28 * inch
    pdf.showPage()


def _draw_shape_page(
    pdf: canvas.Canvas,
    page: InspectionPage,
    page_size: Tuple[float, float],
) -> None:
    if page.shape is None:
        raise ValueError(f"Shape page missing geometry: {page.title}")

    width, height = page_size
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(0.5 * inch, height - 0.55 * inch, page.title)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(0.5 * inch, height - 0.75 * inch, page.caption)
    pdf.drawString(
        0.5 * inch,
        height - 0.95 * inch,
        f"Bounds: {_bounds_text(page.shape)}",
    )

    image = renderer.create_composite_image(page.shape.workplane())
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    max_w = width - 1.0 * inch
    max_h = height - 1.4 * inch
    img_w, img_h = image.size
    scale = min(max_w / img_w, max_h / img_h)
    draw_w, draw_h = img_w * scale, img_h * scale
    x = (width - draw_w) / 2
    y = 0.35 * inch
    pdf.drawImage(
        ImageReader(buffer),
        x,
        y,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True,
        mask="auto",
    )
    pdf.showPage()


def write_mold_inspection_pdf(tooling: MoldTooling, path: str) -> str:
    """Write a polarity-specific multi-page inspection PDF; return path."""
    pages = inspection_pages_for(tooling)
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    page_size = letter
    pdf = canvas.Canvas(path, pagesize=page_size)
    for page in pages:
        if page.summary_lines is not None:
            _draw_summary_page(pdf, page, page_size)
        else:
            _draw_shape_page(pdf, page, page_size)
    pdf.save()
    return path


def generate_example_inspection_pdfs(output_dir: str) -> List[str]:
    """Generate resin and plaster inspection PDFs into output_dir."""
    from efficio.examples.mold_tooling import (
        plaster_triangular_flask_tooling,
        resin_spherical_gear_tooling,
    )

    os.makedirs(output_dir, exist_ok=True)
    outputs = [
        (
            resin_spherical_gear_tooling(),
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
