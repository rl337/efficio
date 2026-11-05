# Efficio

A Python library for 3D CAD modeling using CadQuery.

## Overview

Efficio provides a high-level interface for creating 3D CAD models with a focus on mechanical components, gears, and hardware.

## Features

- 3D primitive shapes (boxes, cylinders, spheres)
- Gear generation (rectangular, trapezoidal, involute, spherical)
- Hardware components (M3 bolts, nuts)
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
fabricated part of a small-vehicle rear transaxle. All shafts are parallel, so
the whole power path uses spur gears:

```
twin-cylinder engine crank -> 12T pinion -> 36T|12T compound idler
  -> 46T ring gear on spur differential -> 12T suns -> D-flat half-shafts
  -> 12 mm hex adapters -> 110 mm wheels            (overall 11.5 : 1)
```

| Group | Parts | Process |
| --- | --- | --- |
| Engine | split block (upper / lower), cylinder head, pistons, connecting rods, crank webs, flywheel, journals, crankpins, wrist pins | block and pistons FDM; head, rods, webs and flywheel 2.5D CNC plate or FDM; pins and journals rod stock |
| Gearbox | left / right side plates with bearing seats, standoffs, crank pinion, compound idler, idler shaft | plates CNC plate or FDM; gears FDM (pinion also CNC) |
| Differential | two carrier halves carrying the ring teeth, two sun gears, four long planets on M3 bolt pins | FDM (planets also CNC) |
| Axles and wheels | half-shafts, pillow blocks, hex wheel adapters, spoked rims, TPU tyres | half-shafts rod stock; rest FDM |

Gears are involute (module 1.5, 25° pressure angle, so 12-tooth pinions do not
undercut) with per-tooth backlash for printed parts.

### Package layout

Parts live in `efficio.objects.powertrain`, grouped by function. Each one takes
its own dimensions, so it can be reused outside this build:

| Module | Contents |
| --- | --- |
| `gears` | `InvoluteGearGeometry` (pure), `SpurGear` (optional hub, round or D bore), `CompoundSpurGear` |
| `engine` | `EngineGeometry` (pure: any cylinder count, bore or stroke, derived bolt patterns, kinematics, rod-sweep check), `EngineBlockHalf`, `CylinderHead`, `CrankWeb`, `ConnectingRod`, `Piston`, `Flywheel` |
| `gearbox` | `BearingPlate`, built from any list of `PlateSeat` / `PlateHole` |
| `differential` | `SpurDifferentialGeometry` (pure), `SpurDifferentialCarrierHalf`, and `sun_gear` / `planet_gear` / `ring_gear`, which are `SpurGear`s |
| `axles` | `PillowBlock` (any `StandardBearing`), `HexWheelAdapter` |
| `wheels` | `Rim`, `Tire` |
| shared | `shafts` (`Shaft`, `Standoff`), `bearings`, `fits`, `profiles` (CadQuery helpers), `planar` (pure 2D) |
| `layout` | `DrivetrainLayout`: composes the engine and differential geometry, works out shaft centres from pitch radii, sets gear rotations so teeth mesh, and checks clearances |

Engine parts have `from_engine(EngineGeometry)` factories. Change the layout
(for example `DrivetrainLayout(engine=EngineGeometry(cylinders=3))`) and every
dependent part, plate hole and shaft length follows. The assembled solids are
checked pair by pair for interference, and the engine is checked across a crank
sweep.

The engine is a kinematic model. It has no valves or ignition, so it is
turned through the gearbox or by hand/motor on the flywheel stub.

```bash
python -m efficio.examples.drivetrain out/drivetrain
python -m efficio --object RearTransaxle --params crank_angle=30 \
    --params cylinders=2 --png rear_transaxle.png
```

This writes `parts/*.stl`, `cnc/*.dxf` mid-height profiles for the CNC-capable
plate parts, `BOM.md` / `bom.csv` (with bearings, fasteners and rod-stock cut
lengths), and `assembly.stl`.

## Development

This project uses Poetry for dependency management and Docker for development environment isolation.

```bash
# Build Docker image
docker build -t efficio .

# Run in Docker container
docker run -it -v $(pwd):/app efficio
```
