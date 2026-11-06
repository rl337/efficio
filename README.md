# Efficio

A Python library for 3D CAD modeling using CadQuery.

## Overview

Efficio provides a high-level interface for creating 3D CAD models with a focus on mechanical components, gears, and hardware.

## Features

- 3D primitive shapes (boxes, cylinders, spheres)
- Gear generation (rectangular, trapezoidal, involute, spherical)
- Fasteners driven by a metric thread catalogue (`efficio.objects.fasteners`:
  `Bolt(MetricThread.M4, length)`, `HexNut`, `BoltChannel`, `M3Bolt(length)`)
- Enclosures, mold tooling and vessels in their own submodules
  (`efficio.objects.enclosures`, `.molds`, `.vessels`)
- Machine build volumes for the Prusa MK4 and Makera Z1 (`efficio.machines`)
- Export to STL, PNG, and SVG formats
- Spatial geometry validation

## Installation

```bash
pip install efficio
```

## Usage

```python
from efficio import Box, Cylinder, RectangularGear

# Create a simple box
box = Box(10, 10, 5)

# Create a gear
gear = RectangularGear(teeth=20, module=2)

# Export to STL
box.export_stl("box.stl")
```

## Drivetrain, engine, wheels and axles

`efficio.examples.drivetrain.rear_transaxle()` lays out and models every
fabricated part of a small-vehicle rear transaxle. The **inline-4 engine** runs
fore-and-aft **above the gearbox** and extends backward, so adding cylinders
makes the car longer, not wider:

```
inline-4 crank (along the car) -> 12T crank pinion -> 48T crown gear   (90 deg turn, 4:1)
  input shaft 16T pinion -> 42T idler gear -> 46T ring on spur differential (2.875:1)
  -> 12T suns -> half-shafts -> 12 mm hex adapters -> 110 mm wheels   (overall 11.5:1)
```

The crown gear is a face gear. At every radius its teeth are the rack that
meshes with the involute pinion (constant base pitch), and the face width is
limited to where the teeth are neither radial nor pointed. The crank is a flat-plane
0/180/180/0 inline-4 layout. The block sits between the gearbox side plates on
**engine mounts**: spacers and bolts (M3 by default; `fastener` on the layout) into the block's side walls.

| Group | Parts | Process |
| --- | --- | --- |
| Engine | split block (upper / lower), cylinder head, pistons, connecting rods, crank webs, flywheel, journals, crankpins, wrist pins, engine mounts | block and pistons FDM; head, rods, webs and flywheel 2.5D CNC plate or FDM; pins and journals rod stock |
| Gearbox | side plates with bearing seats, standoffs, crank pinion, crown gear, input pinion, idler gear, input and idler shafts | plates CNC plate or FDM; crown FDM; spur gears FDM or CNC |
| Differential | two carrier halves carrying the ring teeth, two sun gears, four long planets on M3 bolt pins | FDM (planets also CNC) |
| Axles and wheels | half-shafts, pillow blocks, hex wheel adapters, spoked rims, TPU tyres | half-shafts rod stock or dowel; rest FDM |

Gears are involute (module 1.5, 25° pressure angle, so 12-tooth pinions do not
undercut) with per-tooth backlash for printed parts.

### Package layout

General gears live in `efficio.objects.gears`, so they can be used anywhere:
`InvoluteGearGeometry` and `FaceGearGeometry` (pure); `SpurGear` (optional hub,
round or D bore, cross-pin drive), `CompoundSpurGear` and `CrownGear`;
`GearSystem` (the module, pressure angle and backlash that meshing gears
share); and simple rectangular, trapezoidal and spherical gears. The general
helpers `fits`, `profiles` (CadQuery) and `planar` (pure 2D) sit next to it in
`efficio.objects`.

Drivetrain parts live in `efficio.objects.powertrain`, grouped by function.
Each one takes its own dimensions, so it can be reused outside this build:

| Module | Contents |
| --- | --- |
| `gears` | `DRIVETRAIN_GEAR_SYSTEM` (module 1.5, 25°), `DrivetrainSpurGear` and `DrivetrainCrownGear`: the general gears fixed to that system |
| `engine` | `EngineGeometry` (pure: any cylinder count, bore or stroke, derived bolt patterns, kinematics, rod-sweep check), `EngineBlockHalf`, `CylinderHead`, `CrankWeb`, `ConnectingRod`, `Piston`, `Flywheel` |
| `gearbox` | `BearingPlate`, built from any list of `PlateSeat` / `PlateHole` |
| `differential` | `SpurDifferentialGeometry` (pure), `SpurDifferentialCarrierHalf`, and `sun_gear` / `planet_gear` / `ring_gear`, which are `DrivetrainSpurGear`s |
| `axles` | `PillowBlock` (any `StandardBearing`), `HexWheelAdapter` |
| `wheels` | `Rim`, `Tire` |
| shared | `shafts` (`Shaft`, `Standoff`), `bearings`, `dowels` |
| `layout` | `DrivetrainLayout`: composes the engine and differential geometry, works out shaft centres from pitch radii, sets gear rotations so teeth mesh, and checks clearances |

Axles can be ground steel rod (D-flat drive, tapped end) or **hardwood
dowel** from the hardware store: `DrivetrainLayout.with_dowel_axles()` defaults
to a 1/4" Waddell dowel (Ace item 5980552). Wood can't hold a D-flat, so
the sun gears and wheel hex adapters are driven by a 2 mm cross pin through the
dowel, seated in a slot. The dowel runs through the wheel hub, and a wood screw
in its end grain holds the wheel on. The carrier hub moves to a 6801 bearing,
and the pillow blocks take inch-series R4 bearings. `powertrain.dowels` lists
the Waddell sizes from 1/8" to 1".

Engine parts have `from_engine(EngineGeometry)` factories. Change the layout
(for example `DrivetrainLayout(engine=EngineGeometry(cylinders=6))`) and every
dependent part, plate hole and shaft length follows, while the track stays the same. The assembled solids are
checked pair by pair for interference, and the engine is checked across a crank
sweep.

The engine is a kinematic model. It has no valves or ignition, so it is
turned through the gearbox or by hand/motor on the flywheel stub.

### Sub-assemblies and colour previews

The transaxle is built as nested `Assembly` objects named after the real car
parts: **Engine**, **Gearbox**, **Differential**, **Axles** and **Wheels**.
Each can be built (`gearbox_assembly(layout)`), checked and rendered on its
own, or as part of the whole.

Every `EfficioObject` has an optional `preview_color`. An object without one
inherits its parent's colour; an object with no parent uses the renderer's
current colour (`--color`). Only the sub-assemblies pick colours. Parts
override them only where the material matters, like black tyres and wood
dowels. Previews are shaded colour views (top, front, left side, isometric)
with +Z up and a legend of the sub-assemblies. `--line-art` gives the old
hidden-line drawing.

```bash
python -m efficio.examples.drivetrain out/drivetrain
python -m efficio --object RearTransaxle --params section=GEARBOX --png gearbox.png
python -m efficio --object RearTransaxle --params crank_angle=30 --png rear_transaxle.png
```

This writes `parts/*.stl`, `cnc/*.dxf` mid-height profiles for the CNC-capable
plate parts, `BOM.md` / `bom.csv` (with bearings, fasteners and rod-stock cut
lengths), and `assembly.stl`.


### Reusable involute reference

`InvoluteGearGeometry` is the single source of involute math. Its
`flank_point(radius, side)`, `tooth_outline()` and `outline()` methods are
CadQuery-free; the single-tooth profile can be reused without fixing a sweep
path. Root extensions are radial segments, not generated cutter fillets.
Helical, herringbone and conjugate spherical paths are not implemented here.

`SpurGear` accepts a `MetricModule` catalogue value or a positive numeric module.
`SpurGear.from_tip_radius(...)` preserves the historical outside-radius convention
without introducing a second gear implementation:

```python
from efficio.measures import Millimeter
from efficio.objects.gears import SpurGear

reference = SpurGear.from_tip_radius(
    radius=Millimeter(30), teeth=20, thickness=Millimeter(8),
    lightening_holes=6, engrave_identity=True,
)
```

The factory defaults to 20 degrees and zero backlash. The example derives module
30/11; it does not round the geometry to the `M2.727` engraved display value.
Ordinary `SpurGear` and drivetrain constructors retain their previous defaults.
Lightening and engraving default **off**, so existing drivetrain solids do not
change. A zero bore means an undrilled centre.

Optional holes maintain `minimum_web` at the centre, between holes and inside the
actual sampled root boundary. The same identity ring is reserved with engraving
on or off, so toggling markings does not resize holes. Engraving uses complete glyph-stroke envelopes,
including dots and corners, stays clear of holes and hubs, and leaves at least
`minimum_web` beneath the cut. Small gears skip features that cannot fit;
cross-pinned gears skip both optional features to protect the drive slot.
Inspect `lightening_hole_layout()` and `identity_markings()` to see what will be
cut. `GearMarkingStyle` controls stroke width, depth and text heights in Python.
These conservative geometric checks are not material-specific load or printing
qualification.

The CLI accepts either `--params module=MODULE_1_5` or a numeric module. The
reference can be rendered and exported from its actual geometry:

```sh
python -m efficio --object SpurGear \
  --params module=2.727272727272727 --params teeth=20 \
  --params thickness=8mm --params bore=0mm --params d_flat=false \
  --params pressure_angle=MODERN --params backlash=0mm \
  --params lightening_holes=6 --params engrave_identity=true \
  --png reference.png --stl reference.stl
```

## Development

This project uses Poetry for dependency management. Docker is the reference
development and CI environment; a locked virtual environment is also supported.

```bash
# Build Docker image
docker build -t efficio .

# Run in Docker container
docker run -it -v $(pwd):/app efficio
```

### Non-Docker agent development

Python 3.12 and a local virtual environment are supported on agent VMs without
Docker. The bootstrap uses the same checked-in `poetry.lock` as Docker, including
development dependencies, and installs Efficio editable. Poetry 2.0.1 is installed
in a temporary tool venv and removed afterward; global Python is not modified.

```bash
./scripts/setup_venv.sh
EFFICIO_CHECK_ENV=venv ./run_checks.sh
.venv/bin/python -m efficio --help
# Optional for interactive work:
source .venv/bin/activate
```

Set `PYTHON=/path/to/python3.12` if it is not on PATH. The script can be rerun
without relocking. It requires package-index access and Python's `venv`/pip
support. Keep `.venv` out of version control (already ignored).

A virtual environment does not supply native libraries. On Debian/Ubuntu, common
headless prerequisites are `python3.12-venv`, `build-essential`, `pkg-config`,
`libcairo2-dev`, `libgl1`, and `libglu1-mesa`; the Dockerfile is the reference for
the full system-library set. Have the VM administrator provide missing packages
through the OS package manager. Other OSes may require equivalent libraries or
may not have wheels for the locked CAD packages. Setup finishes with real CAD
solid and Cairo-backed PNG smoke checks to expose missing libraries early.

`run_checks.sh` uses `.venv` if present, otherwise Poetry. Set
`EFFICIO_CHECK_ENV=docker` to force the existing Poetry path in a container,
especially if a host `.venv` is mounted at `/app/.venv` (host venvs are not portable
into containers). The Docker image sets this explicitly, and `.dockerignore` excludes the host
venv from image builds. CI continues to use Docker. The venv runs the same MyPy, Black,
isort and pytest checks; optional tools still run only when installed. Passing
these checks is not a claim of Docker CI, visual CAD inspection or printability.

The shared Black check omits `--diff` so it does not require a multiprocessing
manager socket on restricted VMs; formatting enforcement is unchanged. If the VM
has a read-only home directory, optional runtime cache warnings do not imply
failed checks. Bootstrap keeps its Poetry cache/config in the temporary tool directory;
set `POETRY_CACHE_DIR` to a writable persistent cache to reuse downloads.

### Mold inspection and cutaways

Generate geometry-derived example reports with the supported isolated environment:

```bash
.venv/bin/python -m efficio.inspection --output-dir previews/inspection
```

The resin report uses the reusable 60 mm tip-diameter, 20-tooth, six-hole spur
master without identity engraving. The plaster report uses the triangular flask
exterior master. No experimental spherical tooth design is generated by this
command. Reports include whole parts, sections, a color-preserving exploded board,
a common-plane assembly cutaway, and manufacturing limitations.

`efficio.inspection.section_solid` clips any supported shape by a world-axis
halfspace or slab without changing the source. `inspect_parts` accepts the same
`(name, solid, color)` tuples as the colored renderer. Select components with
`names`, and optionally clip with `axis`, `position`, `mode`, and `slab_thickness`.
A `"mid"` plane comes from the entire input assembly even when isolating only one
component. Cutaway PDFs view a Y section from +Y, the removed side.

A positive silicone intermediate preserves the master's exact surface; the
surrounding envelope is future plaster volume. The cottle does not supply the
production mold, suspension fixture, segmented plaster mold, silicone demolding
cuts or process qualification. Valid CAD solids and printer bounds do not prove
release, leak tightness, fastener strength or casting quality. Review the report's
manufacturing limitations before fabrication.
