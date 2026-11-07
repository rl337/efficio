# Explicit gasket faces and generated parts

`EfficioObject.gasket_faces()` declares named **actual planar CAD faces**.
`object.generate_gasket(name, parameters)` explicitly generates a separate
`GeneratedGasket`; merely calling `shape()` never silently inserts one or changes
an assembly/BOM. Objects without declarations report an unknown-face error.

```python
from efficio.examples.gasket_review import pump_gasket_review
from efficio.objects.gaskets import GasketParameters

body, proposal = pump_gasket_review()
seal = body.generate_gasket(
    "cover_seal",
    GasketParameters(free_thickness=0.33, outer_inset=0.2,
                     inner_inset=0.2, minimum_width=1.0,
                     spread_margin=1.25),
)
free_part = seal.free             # independent EfficioObject, uncompressed
installed = seal.installed_estimate
clearance = seal.clearance_envelope
recess = seal.recess_envelope     # declaration/existing recess, NOT a body edit
```

A `GasketFace` includes a face, an explicit `Opening` for **every inner wire**,
named volumetric `KeepOut`s, the extrusion normal, closed height and closure
explanation. Wire identities must match the face exactly once. Opening roles
are wet cavity, bolt, shaft or explicitly identified other; the generator does
not classify holes by size or silently discard them. The example flange maps
known drawing dimensions and rejects anything else. The pump declares its
single enclosed region on the actual recess floor; bolt holes are outside that
face, not erased or covered by gasket material.

Insets shrink the outer edge and enlarge every opening. Topology changes,
invalid solids, ambiguous declarations, insufficient widths, overfilled recesses
and keep-out intersections raise `ValueError`. Keep-outs are rejection volumes,
not cutters: the implementation cannot secretly notch a sealing band around an
obstruction. The pump explicitly supplies the wet cavity and full cylindrical
rotor-tip swept volumes, rather than checking only one tooth position.

## Minimum in-plane sealing width

The default **1 mm** is a configurable geometric rejection floor, not a preferred
width, material rating or free thickness. It is measured **after both insets**.
The first implementation certifies circles, rectangles and capsules only:
valid contour geometry and analytical area/edge relations establish each convex
primitive, then CAD minimum distances check every outer-to-hole and hole-to-hole
pair. The outer contour's minimum width is also checked. Failure reports the
measured width and limiting boundary pair. CAD comparisons use a 1e-7 mm
numerical tolerance; this is not a manufacturing tolerance.

Concave/narrow-waist contours, splines and unrecognized primitives fail with
`cannot certify minimum sealing width`, even if they might be usable. There is
no sampling-based claim of exhaustive arbitrary-shape validation. This restricted
family avoids missing self-necks within a boundary. A general medial-axis/local
feature-size solver is future work. The generator requires an enclosed opening;
a solid sealing pad is outside this first API's certified scope.

## Distinct artifacts and closure

- **Free part:** inset footprint extruded to specified uncompressed thickness.
- **Installed estimate:** a uniform outward edge offset whose area times closed
  height equals free volume. This is an isotropic approximate-volume-conservation
  construction, not a rubber deformation calculation.
- **Clearance envelope:** the estimated edge offset multiplied by `spread_margin`
  (default 1.25, arbitrary and configurable). It must fit the recess and clear all
  keep-outs. This is not a rigorous worst-case envelope or a safety factor.
- **Recess envelope:** the original declared face extruded to closed height. It
  can describe an existing groove or a proposed cutter; no automatic cut occurs.
- **Hard closure:** closed height is mandatory. Optional actual stop faces are
  checked for coplanarity at that height; `stop_planes_checked` distinguishes
  this geometric evidence from a declared fixture requirement. This does not
  establish clamp load, resin creep, flatness or contact mechanics. No new stops,
  fasteners or compression sleeves are silently manufactured.

The pump supplies actual body lands at the cover plane. Free material stands
proud; hard body/cover contact retains the original gear axial clearance.
The second rectangular flange is an API example whose mating lid/stop fixture
is explicitly unmodeled. Compression set, shear, bulging, friction, swelling,
uneven clamping, adhesion and anisotropic flow are not simulated. Gland fill
below 100% is only a necessary volume check, never proof of good sealing.

## Wider pump review variant (opt-in)

The existing water-feature assembly stays unchanged. `pump_gasket_review()`
builds a matching review body and supports a matching `BlindSupportPart` cover:

| Parameter | Existing recess example | Wider review |
|---|---:|---:|
| Recess width / depth | 1.5 / 0.3 mm | 3.0 / 0.3 mm |
| Inner and outer gasket inset | 0.2 mm each | 0.2 mm each |
| Measured minimum free band | 1.1 mm | **2.6 mm** |
| Free thickness | 0.36 mm | **0.33 mm** |
| Nominal squeeze from dimensions | 16.7% | **9.1%** |
| Exterior cavity offset | 7.5 mm | 10 mm |
| Bolt-placement wall parameter | 10 mm | 16 mm |

Thicknesses and squeeze are provisional examples, not recommendations for an
unselected silicone formulation. The review moves bolts and enlarges the flange;
it is not compatible with the old cover bolt pattern. Chamber and rotor geometry
remain unchanged. Groove-to-bolt ligament is 2.65 mm. The source inner land is
still 0.7 mm, an explicit existing wall-policy exception; this is distinct from
the 2.6 mm gasket band. The 4 mm port remains below the groove with 2.08 mm roof
allowance. The renderer exports a matching review cover and labels all estimated
shapes separately. The independent driver shaft seal remains unselected.

## Manufacturing and physical qualification

No gasket mold is generated or qualified by this API. Free-state CAD can become
a mold master after material-specific shrinkage, venting, fill, surface finish,
parting, release and flash decisions. A 0.33 mm membrane can be awkward to pour
and handle; use thickness trials rather than assuming a wider band solves it.
A thicker gasket needs coordinated recess/port-roof/wall checks. Silicone sold
for mold making is not automatically a qualified reusable water gasket.

Record exact silicone/resin grade, cure and hardness. Test cured thickness,
compression load/recovery, water aging and repeated removal; inspect tears,
flash and contamination. Start with unpowered hydrostatic leakage tests and
separate modest suction/air-ingress checks. Follow the water-pump bench protocol,
keep discharge open with an appropriate bypass, and do not infer pressure,
suction lift or leak-tightness from geometry. No stress, contact-pressure or
mechanical lifetime calculation is included.

The optional cosine bolt-coverage heuristic is deliberately deferred: it would
not strengthen width or sealing validation and its arbitrary normalized 0.7071
threshold must not be mistaken for gasket pressure. Bolt layout/contact analysis
can be a separate future diagnostic.

## Full-face follow-up

The oval pump ring above is retained as an earlier comparison. The explicit
`full_face_pump_review()` now follows the usable entire mating face, including
both nose regions and bolt openings. It uses the opt-in rolling-disk width
construction (`round_to_width=True`), which rounds tips/corners and reports the
removed area. Its minimum width is a construction lower bound, not the earlier
primitive-pair distance measurement. Default width behavior is unchanged.
See [full-face pump gasket](full-face-pump-gasket.md) for geometry, limitations,
residual internal leakage and the coordinated deeper recess/port changes.
