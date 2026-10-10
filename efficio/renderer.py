import io
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cadquery as cq
from PIL import Image, ImageDraw
from reportlab.graphics import renderPM  # type: ignore
from svglib.svglib import svg2rlg  # type: ignore

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
