# Full-face pump gasket review

Richard's correction is implemented as `full_face_pump_review()` in
`efficio/examples/gasket_review.py`. This is an explicit review variant, not a
silent replacement of the earlier water-feature assembly or its bill of materials.
It needs its matching cover. `BlindSupportPart(..., gasket_style="full_face",
full_face_land=...)` constructs a recess from the actual body mating face,
including its figure-eight cavity and four bolt openings. The generated gasket
now extends across both nose/wedge regions omitted by the earlier capsule ring.

## What the old model did and did not leak through

The previous oval groove was 0.7 mm from the wet cavity, with continuous solid
land between them. The nose regions were solid up to the cover plane; absence
of gasket there did not create a modeled open gap. Real resin-to-resin contact
is not a qualified seal, however. Surface texture, flatness and clamp distortion
can let fluid cross a nominal hard contact.

Separately, the CAD intentionally has 0.08 mm clearance above each gear. A slice
of the cavity above all rotor teeth is a connected volume linking the two sides
of the mesh. Tests demonstrate this volume remains clear of the housing, cover,
gasket and rotors at six phases. That is an explicit potential internal leakage
route, independent of the perimeter groove. It does not quantify flow or prove
that the pump cannot develop useful head. Tip clearance, backlash, journal and
shaft leakage, tooth meshing and trapped fluid are additional separate concerns.
A full-face gasket alone cannot establish hydraulic separation between ports.

## Geometry of the revised candidate

- Figure-eight wet opening and four bolt openings are explicitly named; unknown
  topology raises an exception. The gasket includes both nose regions, with
  rounded ends rather than fragile sharp projections.
- A **0.7 mm hard land** remains around cavity, bolt openings and exterior.
  This preserves the original cover datum and closes the recess off from the wet
  cavity in ideal CAD. It is not a pressure-qualified resin sealing contact.
- Free gasket has another **0.4 mm inset** from every recess boundary. These
  margins are explicit, not a claim that silicone reaches the chamber edge.
- Full-face recess is **1.0 mm deep**. Free thickness is **1.05 mm**, giving
  **4.76% nominal dimensional squeeze**, purely a provisional geometry example.
  Actual material, tolerances, compression set and clamp load are unselected.
- Side-port axes move down **0.7 mm**, from z=11.78 to z=11.08, to retain
  **2.08 mm roof** beneath the deeper recess. The 4 mm bores stay open into the
  chamber. Hose roots move with their ports. Body, terminal, seal, shaft and
  casting details remain prototypes, not a build qualification.
- Bolt-placement parameter remains 16 mm and exterior offset 10 mm from the
  preceding wider variant; bolt bosses grow from radius 4.65 to **6 mm** to
  retain room for gasket around the holes. Use the matching cover.
- Chamber, rotor locations and cover plane remain unchanged. Gear end clearance
  stays 0.08 mm; no silicone is placed over the tooth swept volumes.

## Extending the generator without pretending arbitrary widths were measured

`GasketParameters(round_to_width=True)` opts into a separate line/arc construction
for this concave face. Default primitive-distance checks remain unchanged.
The generator offsets inward by half `minimum_width`, requires a valid connected
core with unchanged opening topology, then reconstructs outward with circular
joins. The resulting footprint is a connected rolling-disk construction of the
requested diameter. Reconstruction must remain inside the original footprint;
keep-outs and recess containment are checked afterward as before.

This explicitly rounds/removes tips and corners. The returned
`rounded_area_loss` reports the area removed; it is not hidden in a tolerance.
`minimum_width` is a **lower-bound construction diameter**, not a sampled exact
minimum-distance measurement, when this mode is used. The review requests a
**2 mm lower bound**, wider than the default 1 mm rejection floor. A narrow-waist
example whose erosion disconnects is rejected. Unsupported spline edges,
invalid offsets, split wires and changed topology fail closed. This is CAD-kernel
geometry with numerical tolerances, not proof of mechanical strength.

The estimated installed gasket still uses uniform lateral spread to conserve
approximate volume. Its 1.25 spread multiplier is an arbitrary editable allowance,
not a worst-case physical bound. The full-face candidate passes that geometric
allowance; an earlier, thicker candidate was rejected. The returned installed
and guard solids are not deformation simulations or seals certified for water.

## Validation and what remains

Tests check five explicit openings, coverage of 1 x 1 mm patches on both noses,
no overlap with wet-cavity or full rotor swept-volume keep-outs, hard closure,
port roof, old-groove separation, connected internal face gap and motion at six
angles. The full-face renderer exports body, matching cover, free gasket,
installed estimate, clearance envelope, recess and the residual gap slice;
all are reimported and checked as CAD solids.

No seal force/contact-pressure simulation, gasket mold or material qualification
is included. A continuous gap along an imperfect hard land is still possible in
practice; full-face coverage does not justify a zero-leakage claim. Mold feasibility
must consider thin sheet filling, venting, flash and release around five openings.
Select silicone and resin grades; test cured thickness, recovery, water aging,
repeated assembly and both hydrostatic leakage and air ingress under suction.
Measure flow versus head with a relief/bypass; never dead-head this prototype.

To improve hydraulic separation next, investigate controlled end-face clearances,
qualified end-plate/bearing materials and pressure/flow measurements. Do not
remove clearance blindly or extend elastomer into the rotating envelope. The
shaft seal and actual physical pump performance remain unverified.
