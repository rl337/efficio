"""Printable / CNC powertrain parts.

Subpackages are grouped by function:

* ``gears``        involute geometry (pure) and spur / compound gears
* ``engine``       inline piston engine geometry, block, head, crank, rods, pistons
* ``gearbox``      feature-driven bearing plates
* ``differential`` spur (planet-pair) differential geometry and parts
* ``axles``        pillow blocks and hex drive hubs (half-shafts are ``Shaft``)
* ``wheels``       rims and tyres

Shared modules: ``fits`` (allowances, fasteners, processes), ``bearings``
(catalogue), ``shafts`` (rod-stock shafts, spacers), ``profiles`` (CadQuery
helpers), ``planar`` (pure 2D helpers) and ``layout`` (a complete transaxle
layout composed from the subsystem geometries).
"""
