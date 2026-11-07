# Material- and process-aware wall policy

Efficio's design principle is to declare a **minimum finished-wall budget for a
specific material, process and service**, validate the critical geometry against
it, and record what has not been qualified. There is no universal safe thickness.
A printability minimum is not a pressure, fatigue, clamp or creep design limit.
Existing objects are not retroactively certified by introducing this facility.

`objects/walls.py` provides `WallPolicy` (required features, thresholds, explicit
feature exceptions, material/process/environment/basis/qualification) and
`MaterialWallProfile` (that policy plus separate shrinkage and machining data).
Missing measurements fail validation. Projects supply their own policies.
A geometric pass means only that declared measurements meet declared limits.

`water_pump_dimensions(profile)` and `water_feature_pump(profile=...)` derive
finished CAD from the profile: larger budgets can enlarge bosses, the chamber
offset, blind floors and, where needed for port roof material, gear width and
end plates. A hypothetical 3 mm resin budget is tested as a geometry variant,
not offered as a qualified material. Default interfaces remain unchanged from
the previous prototype except the exterior and the exposed port mouth position.

## This resin experiment's explicit assumptions

The resin grade, cure, water compatibility, modulus, fatigue, creep, flaw size
and allowable pressure are unselected. **2.0 mm is a provisional geometry floor**
chosen to retain the existing blind support floors, not a calculated safe
structural thickness. Manufacturer strength data and specimens are needed before
claiming adequacy. The 0.7 mm inner gasket land is a deliberately narrower sealing
feature with its own provisional 0.6 mm limit; it is supported by the thicker
body beneath and is not treated as a free-standing pressure wall. Clamp loads,
edge breakage and seal behavior remain unverified.

Default measured / derived dimensions (mm):

| Feature | Value | Evidence / scope |
|---|---:|---|
| Side envelope distance from chamber | 7.5 | Exact dilation of union of two circles, before added bosses |
| Offset less end bevel | 6.9 | Conservative planar envelope budget; cavity does not extend to outer ends |
| Boss radius minus hole radius | 3.0 | Before bevel |
| Bolt hole to outer rim, both exposed ends | 2.40 | BRep wire distance, all eight locations |
| Bolt hole to chamber | 3.35 | Center/radius analytical bound |
| Gasket outer edge to case exterior at waist | 2.425215 | Exact BRep wire distance at joint |
| Blind journal end floors | 2.0 | Axial analytical dimension, tested with solid probes |
| Driver seal-seat floor | 4.0 | Cover minus seal pocket depth |
| Side port roof to gasket-joint plane | 2.08 | Port cylinder radius and axial position |
| Inner gasket land | 0.7 | Explicit local sealing-feature exception |

The 7.5 mm main offset is driven by preserving the existing capsule gasket and
leaving at least 2 mm beyond it at the figure-eight waist. It is not asserted to
be the thinnest possible housing. A different gasket path could reduce this
budget, but would be a coordinated sealing redesign. Case volume falls from
46,378.81 to 36,772.86 mm³, approximately 20.71%, versus the prior capsule.

"Uniform distance" means the outer side envelope is the Minkowski sum of the
actual chamber cross-section and a radius-7.5 disk. For this chamber, that is the
union of two enlarged circles. The exterior has constant nearest distance to the
chamber before the bosses; thickness measured along arbitrary rays from the
reentrant waist is not constant. Bosses add local material. Ports intentionally
open through the wall. Blind bores, gasket recess and seal seat create separate
local wall budgets. Each constituent circular lobe/boss has a 0.6 x 0.6 mm
45-degree conical rim at the exposed bottom/body or top/cover. Their unions form
seams where lobes meet; this is not a smooth fillet or a constant-width 2D inset
at every concave junction. No bevel is cut at the gasket joint, port lip, bolt
hole or seal bore.

The plain port axes and diameter remain fixed, but the shorter exterior moves
the centerline mouths from y=+/-21.33 to +/-15.9552 mm. Existing drilling cutters
still extend fully through. No fitted hoses existed to preserve; the eventual
connector design must use the new exterior, whose mouth is curved.

## What the checks do not establish

`measured_housing_interfaces` uses actual BRep wires at selected critical
sections, including the gasket waist and beveled boss rims. The analytical
feature budget checks other named locations. These are not an exhaustive medial
axis/global thickness analysis, FEA, fluid-pressure qualification or toolpath
verification. Open ports have zero closure by design, mating faces touch, and
edge distances tend to zero at boundaries; reporting a single global "minimum"
without feature classification would be misleading. Remaining concerns include
boss-to-case stress concentration, clamp preload, port-to-boss 3D neighborhoods,
thermal/swelling/runout tolerance stack, voids, permeability, surface finish,
fatigue and molding distortion. All prior seal/bearing/retention build gates
remain in force.

## Slip casting and manufacturing allowances

`Process.SLIP_CAST` is distinct from resin casting. The example ceramic profile
has **no wall policy and no shrinkage coefficient**; requesting this pump from
it fails explicitly as unqualified. No ceramic pump geometry or safe thickness
is inferred. A future profile needs clay body, slip formulation, wall-growth
process, drying/firing schedule, fired shrinkage/anisotropy, glazing, water
absorption, dimensional control and service/impact evidence. It may produce a
substantially different form and may prove unsuitable for precision wet-end
journals and gear clearances.

Finished CAD dimensions do not automatically include mold shrinkage.
`tool_dimension(finished)` requires measured linear shrinkage; it computes
`(finished + total_linear_machining_allowance) / (1 - shrinkage)`.
Allowance is total across that dimension, not per face. Unknown shrinkage raises
an error instead of assuming zero. This scalar helper does not compensate
anisotropic fired ceramics, differential shrinkage or a multi-stage mold chain;
those require separately measured transformations. Neither prototype has a
qualified molding-tool scale.

## Physical qualification plan

1. Select exact resin/cure and obtain relevant supplier data. Cast stepped-wall
   coupons at 2, 2.5, 3 and 4 mm, plus representative drilled/beveled bosses,
   gasket lands and blind floors, using the intended tooling and post-machining.
   Include at least five specimens per condition; measure defects and dimensions.
2. Compare dry controls with water-soaked specimens at intended temperature and
   additives. Record mass/dimensions initially and at 1, 7 and 28 days. Establish
   acceptance against the actual gear/seal tolerance budget; do not infer service
   life from these short exposures. Test representative clamp preload, creep,
   impact and repeated assembly before selecting a structural limit.
3. With the seal, fittings and retention resolved, fill with water, remove trapped
   air and use a guarded low-energy open-standpipe test. Start at 0.1 m and then
   the provisional 0.3 m operating head; hold 15 minutes and inspect leakage,
   deformation and cracks. A supervised 0.5 m screening step is an experiment,
   not a qualified proof-pressure multiplier. No compressed-air pressure test.
   Stop on leakage, cracking, permanent deformation or joint movement. Do not
   extrapolate these heads into a pressure rating.
4. Establish maximum service/blockage pressure from the selected drive and relief
   system before engineering an actual proof/cyclic test. Then run the existing
   flow/head and supervised endurance protocol. Use results to revise the policy,
   with material batch, process, test conditions and uncertainty recorded.

## Evidence

[Formlabs' design specifications](https://formlabs.com/support/Design-Specs/)
state their printability guidelines apply to a particular resin, printer and
layer thickness. Those limits are not adopted as structural pump limits.
[Smooth-On's technical-document guidance](https://support.smooth-on.com/knowledgebase.php?article=42)
identifies product-specific cure and physical-property data and directs users
to support for additional mechanical properties. Neither source establishes a
safe wall for this unselected material/application.
