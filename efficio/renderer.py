import io

from typing import Tuple

import cadquery as cq
from PIL import Image

from svglib.svglib import svg2rlg  # type: ignore
from reportlab.graphics import renderPM  # type: ignore

def create_view_svg(shape: cq.Workplane, projection_dir: Tuple[float, float, float]) -> bytes:
    svg_buffer = io.BytesIO()
    cq.exporters.exportShape(shape, svg_buffer, exportType='SVG', opt={"projectionDir": projection_dir})
    return svg_buffer.getvalue()

def convert_svg_to_png(svg_data: bytes) -> Image.Image:
    svg_string = svg_data.decode('utf-8')
    drawing = svg2rlg(io.StringIO(svg_string))
    png_buffer = io.BytesIO()
    renderPM.drawToFile(drawing, png_buffer, fmt="PNG")
    png_buffer.seek(0)
    return Image.open(png_buffer)

def create_composite_image(obj: cq.Workplane) -> Image.Image:
    # Generate SVGs for different views
    svg_top = create_view_svg(obj, (0, 0, 1))
    svg_front = create_view_svg(obj, (0, 1, 0))
    svg_left = create_view_svg(obj, (1, 0, 0))
    svg_iso = create_view_svg(obj, (1, 1, 1))

    # Convert SVGs to PNGs
    img_top = convert_svg_to_png(svg_top)
    img_front = convert_svg_to_png(svg_front)
    img_left = convert_svg_to_png(svg_left)
    img_iso = convert_svg_to_png(svg_iso)

    # Determine the size of the composite image
    width, height = img_top.size
    composite_width = width * 2
    composite_height = height * 2

    # Create a new blank image
    composite_image = Image.new('RGB', (composite_width, composite_height), 'white')

    # Paste each view into the composite image
    composite_image.paste(img_top, (0, 0))
    composite_image.paste(img_front, (width, 0))
    composite_image.paste(img_left, (0, height))
    composite_image.paste(img_iso, (width, height))

    return composite_image


