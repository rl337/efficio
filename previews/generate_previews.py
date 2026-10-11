"""Generate PNG previews and mold inspection PDFs via the Efficio renderer."""

from __future__ import annotations

import os
import sys
import traceback
from typing import Callable, List, Optional, Tuple

from efficio import renderer
from efficio.examples.mold_tooling import (
    plaster_triangular_flask_tooling,
    resin_spherical_gear_tooling,
)
from efficio.inspection import generate_example_inspection_pdfs
from efficio.measures import Inch, Millimeter
from efficio.objects.gears import RectangularGear, SphericalGear, TrapezoidalGear
from efficio.objects.mold_tooling import ToolingSection
from efficio.objects.shapes import Shape
from efficio.objects.vases import TriangularFlaskVase

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

ShapeFactory = Callable[[], Optional[Shape]]


def save(name: str, shape: Optional[Shape]) -> None:
    if shape is None:
        raise ValueError(f"{name}: shape() returned None")
    path = os.path.join(OUT_DIR, f"{name}.png")
    print(f"Rendering {name}...", flush=True)
    image = renderer.create_composite_image(shape.workplane())
    image.save(path, "PNG")
    print(f"  wrote {path} ({os.path.getsize(path)} bytes)", flush=True)


def _cottle_factory(section: ToolingSection) -> ShapeFactory:
    def factory() -> Optional[Shape]:
        return section.geometry

    return factory


def main() -> int:
    jobs: List[Tuple[str, ShapeFactory]] = []

    # Gears worked on in the spherical-gear redesign / mold fixture
    jobs.append(
        (
            "spherical_gear_20mm_16t",
            lambda: SphericalGear(radius=Millimeter(20), tooth_count=16).shape(),
        )
    )
    jobs.append(
        (
            "spherical_gear_2in_16t_resin_master",
            lambda: SphericalGear(radius=Inch(1), tooth_count=16).shape(),
        )
    )
    jobs.append(
        (
            "rectangular_gear_30mm_16t",
            lambda: RectangularGear(Millimeter(30), 16, Millimeter(8)).shape(),
        )
    )
    jobs.append(
        (
            "trapezoidal_gear_30mm_16t",
            lambda: TrapezoidalGear(Millimeter(30), 16, Millimeter(8)).shape(),
        )
    )

    # Masters used by mold examples
    jobs.append(
        (
            "triangular_flask_vase",
            lambda: TriangularFlaskVase(
                width=Millimeter(80),
                height=Millimeter(140),
                depth=Millimeter(45),
                neck=Millimeter(24),
            ).shape(),
        )
    )

    # Resin mold tooling
    resin = resin_spherical_gear_tooling()
    jobs.append(("resin_gear_silicone_negative", resin.silicone_shape))
    for section in resin.cottle_sections():
        jobs.append((f"resin_gear_cottle_{section.name}", _cottle_factory(section)))

    # Plaster mold tooling
    plaster = plaster_triangular_flask_tooling()
    jobs.append(("plaster_vase_silicone_positive", plaster.silicone_shape))
    for section in plaster.cottle_sections():
        jobs.append((f"plaster_vase_cottle_{section.name}", _cottle_factory(section)))

    failures = 0
    for name, factory in jobs:
        try:
            save(name, factory())
        except Exception:
            failures += 1
            print(f"FAILED {name}:", flush=True)
            traceback.print_exc()

    try:
        print("Writing mold inspection PDFs...", flush=True)
        for path in generate_example_inspection_pdfs(OUT_DIR):
            print(f"  wrote {path} ({os.path.getsize(path)} bytes)", flush=True)
    except Exception:
        failures += 1
        print("FAILED mold inspection PDFs:", flush=True)
        traceback.print_exc()

    print(f"Done. failures={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
