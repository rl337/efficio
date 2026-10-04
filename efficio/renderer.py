import io
import math
from typing import List, Optional, Tuple

import cadquery as cq
from PIL import Image, ImageDraw
from reportlab.graphics import renderPM  # type: ignore
from svglib.svglib import svg2rlg  # type: ignore

Projection = Tuple[float, float, float]


def _shape_values(shape: cq.Workplane) -> List[cq.Shape]:
    return [value for value in shape.vals() if isinstance(value, cq.Shape)]


def _bounds(shape: cq.Workplane) -> Optional[Tuple[float, float, float, float, float, float]]:
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
    scale = 10**exponent
    normalized = raw / scale
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return nice * scale


def create_grid(size: float, spacing: float, thickness: float) -> cq.Workplane:
    grid = cq.Workplane("XY")
    count = int(math.ceil(size / spacing))
    for index in range(-count, count + 1):
        coordinate = index * spacing
        line_thickness = thickness * (2 if index == 0 else 1)
        grid = grid.add(
            cq.Workplane("XY")
            .box(line_thickness, 2 * size, thickness, centered=True)
            .translate((coordinate, 0, 0))
        )
        grid = grid.add(
            cq.Workplane("XY")
            .box(2 * size, line_thickness, thickness, centered=True)
            .translate((0, coordinate, 0))
        )
    return grid


def _preview_compound(shape: cq.Workplane, show_grid: bool) -> cq.Compound:
    # Never mutate the caller's Workplane. Preview generation must be idempotent.
    values = _shape_values(shape)
    if not values:
        raise ValueError("Cannot preview an empty workplane")

    if show_grid:
        bounds = _bounds(shape)
        assert bounds is not None
        extent = max(
            bounds[3] - bounds[0],
            bounds[4] - bounds[1],
            bounds[5] - bounds[2],
        )
        spacing = _nice_grid_spacing(extent)
        size = max(spacing * 5, math.ceil((extent * 0.75) / spacing) * spacing)
        thickness = max(extent * 0.0005, 0.005)
        values.extend(_shape_values(create_grid(size, spacing, thickness)))

    return cq.Compound.makeCompound(values)


def create_view_svg(
    shape: cq.Workplane,
    projection_dir: Projection,
    *,
    width: int = 640,
    height: int = 640,
    show_grid: bool = True,
) -> bytes:
    compound = _preview_compound(shape, show_grid)
    svg = cq.exporters.svg.getSVG(
        compound,
        opts={
            "width": width,
            "height": height,
            "marginLeft": 35,
            "marginTop": 35,
            "projectionDir": projection_dir,
            "strokeWidth": 1,
            "strokeColor": (0, 0, 0),
            "hiddenColor": (150, 150, 170),
            "showAxes": True,
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


def _annotate(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    draw.rectangle((0, 0, result.width, 44), fill="white")
    draw.text((12, 8), title, fill="black")
    if subtitle:
        draw.text((12, 25), subtitle, fill=(70, 70, 70))
    return result


def _dimensions(shape: cq.Workplane) -> str:
    bounds = _bounds(shape)
    if bounds is None:
        return "empty"
    x = bounds[3] - bounds[0]
    y = bounds[4] - bounds[1]
    z = bounds[5] - bounds[2]
    return f"{x:.2f} x {y:.2f} x {z:.2f} mm"


def create_composite_image(
    obj: cq.Workplane,
    *,
    show_grid: bool = True,
    annotate: bool = True,
) -> Image.Image:
    views = (
        ("TOP +Z", (0, 0, 1)),
        ("FRONT +Y", (0, 1, 0)),
        ("LEFT +X", (1, 0, 0)),
        ("ISOMETRIC", (-1.75, 1.1, 5)),
    )
    dimensions = _dimensions(obj)
    images: List[Image.Image] = []
    for title, projection in views:
        image = convert_svg_to_png(
            create_view_svg(obj, projection, show_grid=show_grid)
        )
        if annotate:
            image = _annotate(image, title, dimensions)
        images.append(image)

    width, height = images[0].size
    composite = Image.new("RGB", (width * 2, height * 2), "white")
    for index, image in enumerate(images):
        composite.paste(image, ((index % 2) * width, (index // 2) * height))
    return composite
