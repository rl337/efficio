# Integral water-pump tube terminals

Both ports now have real open-bore hose barbs fused into the pump body. The
reusable `HoseBarbDimensions` / `HoseBarb` classes live in `objects/connectors`;
the concrete selection lives in `examples/water_feature_pump.py`.

## Provisional interface

- Flexible hose **8 mm ID, nominal 12 mm OD**. The choice leaves a 2 mm radial
  resin wall around the retained 4 mm flow passage; a 6 mm stem would leave only
  1 mm. This is a provisional fit experiment, not a selected hose product.
- Stem OD 8.0 mm, two barb peaks OD 8.8 mm, each with a 3 mm entry taper and a
  rear shoulder. Nominal stretch over peaks is 10%; actual strain and holding
  force depend on hose grade, hardness, tolerances and temperature.
- Hose slides 17 mm onto each terminal, stopping at |y|=21 mm. A 5 mm straight
  clamp land occupies |y|=21..26; barb tapers occupy 26..29 and 32..35 mm;
  terminal tip is at |y|=38 mm. Overall tip-to-tip span is 76 mm.
- Select a non-cutting clamp with axial width <=5 mm and a swept outside envelope
  <=14.8 mm for this layout. The space allowance includes hose and clamp but is
  not a selected clamp model, torque specification or tool-access certification.
- Bores are 4 mm throughout and overlap the existing side drilling into the
  chamber. The two bosses start at |y|=12 mm inside the housing. No separate
  adhesive or threaded wet joint is introduced. Hoses/clamps are BOM hardware,
  not falsely rendered as installed components.
- Inlet is +Y for left driver CCW viewed from +Z; outlet is -Y. Both terminals
  have identical geometry; reversing rotation reverses the roles.

## Integral versus replaceable

This revision uses integral cast/machined barbs to preserve the organic body and
avoid adding an unselected thread/seal interface. Damaged barbs require replacing
or reworking the body. A replaceable commercial fitting could improve serviceability
but needs a supplier drawing, reinforced socket/boss, positive retention and a
qualified static seal; none is implied by this model. The reusable barb class can
produce a standalone shape, but that alone is not a complete replaceable fitting.

Barbs introduce casting undercuts. Use split side inserts around the barbs or
another validated multi-piece mold strategy; do not assume a straight axial mold
pull. The central bore can use a supported straight core or post-cast aligned
4 mm drilling. Polish sealing surfaces and remove flash without reducing the
2 mm wall. Mold tooling, draft, shrinkage, root fillets and demolding have not
been validated. The abrupt barb/root transitions need coupon and pull testing;
CAD validity does not establish fracture resistance.

## Gasket-roof correction

Adding terminals exposed a missing term in the previous wall check: the gasket
recess removes 0.3 mm above the port. The previous 2.08 mm joint-plane budget was
only 1.78 mm to the recess floor. Both bores now sit 0.3 mm lower, at z=11.78,
and the check measures to the recess floor, yielding 2.08 mm. Chamber, rotors,
shafts, gasket, bolt pattern, seal seat, organic case and exposed bevels remain.
The named wall check is now `port_roof_to_gasket`. Larger provisional material
budgets also enlarge terminal stems and nominal hose size; physical qualification
still requires the actual material and hose pair.

## Verified geometry and limits

Tests check single valid fused body, overlapping terminal/side-drilling/chamber
voids, no residual material blocking those voids, six sampled rotor poses, and
hose/clamp envelopes clear of the case, cover and remaining parts. Conservative
7 mm diameter straight tool columns along case-bolt axes are also checked.
These do not simulate hose deformation, bend radius, clamp screw orientation,
assembly forces, external routing or handle access. Support hoses independently
so they do not cantilever their weight or bend loads onto the resin barbs.

## Physical fit and wet tests before running

1. Cast/machine barb coupons with the exact resin/cure; measure stem, peaks,
   bore, concentricity and surface defects. Try the exact hose and clamp, wet
   and dry, recording insertion force, damage and achievable engagement. Do not
   force a hard or undersized tube onto brittle resin.
2. Provisional screening: apply 10 N axial pull for 60 seconds, dry and after
   water conditioning, with no slip/cracking; this is an experiment, not a
   certified retention load. Set the final requirement from installation loads
   and pressure thrust, with a justified margin and repeated-cycle evidence.
3. Use the existing filled-water standpipe tests (0.1, 0.3, then supervised 0.5 m
   only if prior steps pass). Collect leaks and inspect both terminal roots and
   hose lands. No visible leakage or cracking is acceptable. No compressed-air
   proof test, deadheading, or implied pressure rating.
4. Start with flooded suction and monitor inlet bubbles, flow and hose shape.
   A hose that does not leak water outward may still admit air under suction.
   Select tubing explicitly suitable for the anticipated vacuum; do not assume
   soft silicone remains open or is vacuum-rated. Stop on collapse, persistent
   bubbles, leakage, slip or rising motor load. Recheck after thermal cycles and
   the supervised endurance trial. Pump, seal and bearing qualification remain
   outstanding.

Manufacturer references are context, not ratings for this CAD:
[Cole-Parmer's barbed fittings](https://www.coleparmer.com/p/cole-parmer-hose-barb-fittings-straight-reducer-natural-polycarbonate/91604)
use a product-specific interference design; their pressure claims are not applied
here. [Saint-Gobain's tubing selection chart](https://www.biopharm.saint-gobain.com/sustainable-tubing)
distinguishes vacuum suitability by tubing construction, reinforcing that hose
material name alone is insufficient.
