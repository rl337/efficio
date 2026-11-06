import io
import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cadquery as cq
import numpy as np
from PIL import Image, ImageDraw
from reportlab.graphics import renderPM  # type: ignore
from svglib.svglib import svg2rlg  # type: ignore

from efficio import preview
from efficio.objects.base import DEFAULT_PREVIEW_COLOR, Color, EfficioObject

Projection = Tuple[float, float, float]


@dataclass(frozen=True)
class PreviewStyle:
    """Rendering controls for engineering inspection previews."""

    panel_width: int = 1200
    panel_height: int = 1200
    object_stroke_width: float = 0.55
    hidden_line_gray: int = 205
    guide_gray: int = 232
    guide_axis_gray: int = 205
    guide_width: int = 1
    guide_axis_width: int = 2
    margin: int = 55


DEFAULT_PREVIEW_STYLE = PreviewStyle()


def _shape_values(shape: cq.Workplane) -> List[cq.Shape]:
    return [value for value in shape.vals() if isinstance(value, cq.Shape)]


def _bounds(
    shape: cq.Workplane,
) -> Optional[Tuple[float, float, float, float, float, float]]:
    values = _shape_values(shape)
    if not values:
        return None
    boxes = [value.BoundingBox() for value in values]
    return (
        min(box.xmin for box in boxes),
        min(box.ymin for box in boxes),
        min(box.zmin for box in boxes),
        max(box.xmax for box in boxes),
        max(box.ymax for box in boxes),
        max(box.zmax for box in boxes),
    )


def _nice_grid_spacing(extent: float) -> float:
    if extent <= 0:
        return 10.0
    raw = extent / 8.0
    exponent = math.floor(math.log10(raw))
    scale = float(10**exponent)
    normalized = raw / scale
    nice = (
        1.0
        if normalized <= 1
        else 2.0 if normalized <= 2 else 5.0 if normalized <= 5 else 10.0
    )
    return nice * scale


def _preview_compound(shape: cq.Workplane) -> cq.Compound:
    values = _shape_values(shape)
    if not values:
        raise ValueError("Cannot preview an empty workplane")
    return cq.Compound.makeCompound(values)


def create_view_svg(
    shape: cq.Workplane,
    projection_dir: Projection,
    *,
    style: PreviewStyle = DEFAULT_PREVIEW_STYLE,
) -> bytes:
    # Reference guides are intentionally NOT CAD solids. Keeping them out of the
    # projected compound prevents guide geometry from occluding or changing the part.
    svg = cq.exporters.svg.getSVG(
        _preview_compound(shape),
        opts={
            "width": style.panel_width,
            "height": style.panel_height,
            "marginLeft": style.margin,
            "marginTop": style.margin,
            "projectionDir": projection_dir,
            "strokeWidth": style.object_stroke_width,
            "strokeColor": (0, 0, 0),
            "hiddenColor": (
                style.hidden_line_gray,
                style.hidden_line_gray,
                style.hidden_line_gray,
            ),
            "showAxes": False,
        },
    )  # type: ignore
    return str(svg).encode("utf8")


def convert_svg_to_png(svg_bytes: bytes) -> Image.Image:
    drawing = svg2rlg(io.BytesIO(svg_bytes))
    if drawing is None:
        raise RuntimeError("SVG renderer returned no drawing")
    png_buffer = io.BytesIO()
    try:
        renderPM.drawToFile(drawing, png_buffer, fmt="PNG")
    except Exception as exc:
        raise RuntimeError(f"Error converting drawing to PNG: {exc}") from exc
    png_buffer.seek(0)
    image = Image.open(png_buffer)
    image.load()
    return image.convert("RGB")


def _draw_guides(
    image: Image.Image,
    extent: float,
    style: PreviewStyle,
) -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    spacing_mm = _nice_grid_spacing(extent)

    # These are screen-space inspection guides, deliberately pale and thin.
    # They are references, not projected geometry.
    usable = min(result.width, result.height) - 2 * style.margin
    divisions = max(4, int(round(extent / spacing_mm)) + 2)
    pixel_spacing = usable / divisions
    cx, cy = result.width / 2, result.height / 2

    guide = (style.guide_gray,) * 3
    axis = (style.guide_axis_gray,) * 3
    for index in range(-divisions, divisions + 1):
        x = int(round(cx + index * pixel_spacing))
        y = int(round(cy + index * pixel_spacing))
        if 0 <= x < result.width:
            draw.line(
                (x, style.margin, x, result.height - style.margin),
                fill=guide,
                width=style.guide_width,
            )
        if 0 <= y < result.height:
            draw.line(
                (style.margin, y, result.width - style.margin, y),
                fill=guide,
                width=style.guide_width,
            )
    draw.line(
        (int(cx), style.margin, int(cx), result.height - style.margin),
        fill=axis,
        width=style.guide_axis_width,
    )
    draw.line(
        (style.margin, int(cy), result.width - style.margin, int(cy)),
        fill=axis,
        width=style.guide_axis_width,
    )
    return result


def _annotate(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    draw.rectangle((0, 0, result.width, 48), fill="white")
    draw.text((14, 8), title, fill="black")
    if subtitle:
        draw.text((14, 27), subtitle, fill=(90, 90, 90))
    return result


def _dimensions(shape: cq.Workplane) -> str:
    bounds = _bounds(shape)
    if bounds is None:
        return "empty"
    x, y, z = bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2]
    return f"{x:.2f} x {y:.2f} x {z:.2f} mm"


def create_composite_image(
    obj: cq.Workplane,
    *,
    show_grid: bool = True,
    annotate: bool = True,
    style: PreviewStyle = DEFAULT_PREVIEW_STYLE,
) -> Image.Image:
    views = (
        ("TOP +Z", (0, 0, 1)),
        ("FRONT +Y", (0, 1, 0)),
        ("LEFT +X", (1, 0, 0)),
        ("ISOMETRIC", (-1.75, 1.1, 5)),
    )
    dimensions = _dimensions(obj)
    bounds = _bounds(obj)
    if bounds is None:
        raise ValueError("Cannot preview an empty workplane")
    extent = max(bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])

    images: List[Image.Image] = []
    for title, projection in views:
        image = convert_svg_to_png(create_view_svg(obj, projection, style=style))
        if show_grid:
            image = _draw_guides(image, extent, style)
        if annotate:
            image = _annotate(image, title, dimensions)
        images.append(image)

    width, height = images[0].size
    composite = Image.new("RGB", (width * 2, height * 2), "white")
    for index, image in enumerate(images):
        composite.paste(image, ((index % 2) * width, (index // 2) * height))
    return composite


# --------------------------------------------------------------------------
# Colour previews
# --------------------------------------------------------------------------

ColoredSolid = Tuple[str, cq.Shape, Color]
ColoredTriangle = Tuple[preview.Triangle, Color]
LEGEND_ROW_HEIGHT = 34


def tessellate_parts(
    parts: Sequence[ColoredSolid],
    tolerance: float = 0.1,
    angular_tolerance: float = 0.3,
) -> List[ColoredTriangle]:
    """Triangulate each solid once so every view can reuse the mesh."""
    triangles: List[ColoredTriangle] = []
    for _, solid, color in parts:
        vertices, faces = solid.tessellate(tolerance, angular_tolerance)
        points = [(v.x, v.y, v.z) for v in vertices]
        for a, b, c in faces:
            triangles.append(((points[a], points[b], points[c]), color))
    return triangles


def create_color_view(
    triangles: Sequence[ColoredTriangle],
    view: preview.View,
    *,
    style: PreviewStyle = DEFAULT_PREVIEW_STYLE,
    show_grid: bool = True,
) -> Image.Image:
    width, height = style.panel_width, style.panel_height
    # Keep vertex depths: a triangle's average depth cannot resolve crossing
    # surfaces, or a small foreground feature over a large sloping triangle.
    projected = [
        ([view.project(point) for point in triangle], color, triangle)
        for triangle, color in triangles
    ]
    viewport = preview.Viewport.fit(
        ((x, y) for points, _, _ in projected for x, y, _ in points),
        width,
        height,
        style.margin,
    )
    image = Image.new("RGB", (width, height), "white")
    if show_grid:
        extent = max(width, height) / viewport.scale
        image = _draw_guides(image, extent, style)
    pixels = np.array(image)
    depths = np.full((height, width), -np.inf)
    for points, color, triangle in projected:
        screen = [viewport.to_pixels(x, y) for x, y, _ in points]
        (ax, ay), (bx, by), (cx, cy) = screen
        area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        # Edge-on/degenerate triangles have no area and must not draw lines
        # through visible faces. Both windings otherwise use the same test.
        if abs(area) < 1e-12:
            continue
        left = max(0, math.ceil(min(ax, bx, cx) - 0.5))
        right = min(width - 1, math.floor(max(ax, bx, cx) - 0.5))
        top = max(0, math.ceil(min(ay, by, cy) - 0.5))
        bottom = min(height - 1, math.floor(max(ay, by, cy) - 0.5))
        if left > right or top > bottom:
            continue
        shaded = preview.shade(color, preview.triangle_normal(triangle), view)
        xs = np.arange(left, right + 1, dtype=float)[None, :] + 0.5
        # Bound temporary memory even for a triangle covering the whole panel.
        for row in range(top, bottom + 1, 64):
            end = min(row + 64, bottom + 1)
            ys = np.arange(row, end, dtype=float)[:, None] + 0.5
            wa = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / area
            wb = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / area
            wc = 1.0 - wa - wb
            # Inclusive edges avoid cracks on shared coplanar tessellation
            # edges. Equal-depth samples retain their first surface.
            inside = (wa >= -1e-10) & (wb >= -1e-10) & (wc >= -1e-10)
            depth = wa * points[0][2] + wb * points[1][2] + wc * points[2][2]
            current = depths[row:end, left : right + 1]
            visible = inside & (depth > current)
            current[visible] = depth[visible]
            pixels[row:end, left : right + 1][visible] = shaded
    return Image.fromarray(pixels)


def _draw_legend(
    image: Image.Image, legend: Sequence[Tuple[str, Color]], top: int
) -> None:
    draw = ImageDraw.Draw(image)
    x = 14
    for name, color in legend:
        draw.rectangle((x, top + 8, x + 22, top + 26), fill=color, outline="black")
        draw.text((x + 30, top + 11), name, fill="black")
        x += 40 + 8 * len(name) + 24


def create_color_composite_image(
    parts: Sequence[ColoredSolid],
    *,
    legend: Sequence[Tuple[str, Color]] = (),
    style: PreviewStyle = DEFAULT_PREVIEW_STYLE,
    views: Sequence[preview.View] = preview.STANDARD_VIEWS,
    annotate: bool = True,
) -> Image.Image:
    """Shaded, colour-coded 2x2 preview (top, front, side, isometric)."""
    if not parts:
        raise ValueError("Cannot preview an empty object")
    compound = cq.Compound.makeCompound([solid for _, solid, _ in parts])
    box = compound.BoundingBox()
    dimensions = f"{box.xlen:.2f} x {box.ylen:.2f} x {box.zlen:.2f} mm"
    triangles = tessellate_parts(parts)

    panels: List[Image.Image] = []
    for view in views:
        panel = create_color_view(triangles, view, style=style)
        if annotate:
            panel = _annotate(panel, view.title, dimensions)
        panels.append(panel)

    width, height = panels[0].size
    columns = 2
    rows = (len(panels) + 1) // columns
    legend_height = LEGEND_ROW_HEIGHT if legend else 0
    composite = Image.new(
        "RGB", (width * columns, height * rows + legend_height), "white"
    )
    for index, panel in enumerate(panels):
        composite.paste(panel, ((index % columns) * width, (index // columns) * height))
    if legend:
        _draw_legend(composite, legend, height * rows)
    return composite


def object_preview_parts(
    obj: EfficioObject, current: Color = DEFAULT_PREVIEW_COLOR
) -> Tuple[List[ColoredSolid], List[Tuple[str, Color]]]:
    """Coloured solids and legend for any object.

    Objects that know their parts (assemblies) colour each part through its
    inherited ``preview_color``; anything else is drawn in its own resolved
    colour.
    """
    parts_method = getattr(obj, "preview_parts", None)
    legend_method = getattr(obj, "preview_legend", None)
    if callable(parts_method):
        parts: List[ColoredSolid] = list(parts_method(current))
        legend: List[Tuple[str, Color]] = (
            list(legend_method(current)) if callable(legend_method) else []
        )
        return parts, legend
    shape = obj.shape()
    if shape is None:
        raise ValueError(f"{type(obj).__name__} has no geometry")
    color = obj.resolved_preview_color(current)
    solids = _shape_values(shape.workplane())
    name = type(obj).__name__
    return [(name, solid, color) for solid in solids], [(name, color)]


def create_object_preview(
    obj: EfficioObject,
    current: Color = DEFAULT_PREVIEW_COLOR,
    *,
    style: PreviewStyle = DEFAULT_PREVIEW_STYLE,
) -> Image.Image:
    parts, legend = object_preview_parts(obj, current)
    return create_color_composite_image(parts, legend=legend, style=style)
