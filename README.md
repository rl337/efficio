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

## Development

This project uses Poetry for dependency management and Docker for development environment isolation.

```bash
# Build Docker image
docker build -t efficio .

# Run in Docker container
docker run -it -v $(pwd):/app efficio
```
