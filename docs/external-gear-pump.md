# External-gear pump: educational prototype and bench gates

This is a geometric design **candidate for a working pump**, not a demonstrated
working pump. No liquid has been circulated. There is no measured flow, pressure,
torque, volumetric efficiency, leak rate, life or resin compatibility. The engine
is an externally motor-driven educational mechanism, not a combustion engine.

## Reusable design and engine configuration

`objects/pumps/geometry.py` contains pure sizing/validation. `external_gear.py`
uses the shared `SpurGear`/involute geometry, with separate body, cover, two round-journal
shafts, two cross-pinned rotors and four set-screw collar interfaces. `strainer.py` is a separate
parameterized housing, removable cap and perforated insert. These objects have no
engine dependency. `examples/pumped_engine.py` chooses the engine dimensions and
placements; the earlier resin/lubrication examples remain available unchanged.

| Engine review choice | CAD value |
|---|---|
| Pump rotors | module 1, 12 teeth each, 25 degree pressure angle, 6 mm face |
| Rotor centers / tip diameter | 12 / 14 mm |
| Candidate gaps | 0.15 mm radial tip, 0.10 mm each face, 0.05 mm tooth backlash |
| Shafts / journal bores | nominal 4 mm round lands with outboard D flats; 4.2 mm journal bores |
| Case / cover | 3 mm base, 5 mm outside wall allowance, 3 mm cover |
| Ports / tubing | 3 mm bore, tubing 5 mm OD |
| Drive | module 2, crank 18T / pump 22T; 40 mm centers; pump speed = 9/11 crank speed, opposite direction |
| Pickup / downstream insert | geometric hole diameters 0.5 / 0.4 mm; **not rated filter media** |
| Pump coordinates | driver axis X=-40, Z=0; body starts Y=-35 mm |
| Drive gear plane | Y=-7.5 through -2.5 mm, on existing crank D stub |

The mounting adapter has four coaxial pump clamp holes/spacers and two long
engine spacers. Its two engine holes are actually drilled through a variant of
the front support at X=+/-18, Z=40 mm (3.3 mm diameter). The other original engine
solids retain their geometry and placements. Liners remain continuous. The
adapter's stiffness and long-bolt alignment are unqualified; metal is preferred
for the first fixture. Bolts, nuts, guard, hose clips and external gear collars
are selection/assembly work, not modeled installed hardware or counted purchases.
The filter currently requires an independent clamp/support.

## Direction and actual connectivity

In the pump's local XY plane, driver is at (0,0), idler at (12,0), axes +Z.
A clockwise driver viewed from +Z takes fluid from -Y and carries it around the
outside of both rotors to +Y. Reversal exchanges inlet/outlet. In the engine,
increasing crank angle produces a **counterclockwise local pump driver**, so
local +Y (world lower Z port) is suction and local -Y (upper Z port) is delivery.
The animated-angle convention must be matched to the actual motor wiring.

Modeled path: sump pickup aperture → perforated pickup insert → hollow suction
line → lower pump port / adjacent gear pocket → outer tooth-space transport
**anticipated, not simulated** → upper port → hollow pressure line → actual
perforated strainer chamber → delivery line → existing gallery → four under-liner
jets and two bearing-face outlets. Gravity return/wetting are not simulated.
The bearing outlets do not become drilled crank oilways; compatibility with
shielded bearings remains unresolved. No solid wall is used as a pretend feed.

The relief takeoff is before the strainer, at (-86,0,16). Return interface is
(-86,12,16), tied to suction. The **12 mm valve gap is real and open**. A selected,
independently rated relief valve and fittings must bridge it before pressure
operation. This is a bypass provision, not an installed pressure regulator.
Returning to suction recirculates heat and can aggravate aeration; a separately
routed submerged sump return is preferable for sustained bypass operation.
Never cap the takeoff and describe the circuit as protected. Reverse operation
would also require moving the relief/filter arrangement; this layout is intended
for one crank direction.

Boolean tests check connected suction and delivery voids, apertures through the
strainer, port access at several rotor phases, absence of fluid-core intrusion
into neighboring solids, mesh clearances and assembly interference at sampled
poses. Positive face/tip gaps mean the pump's free volume is connected even when
stationary: this exposes a **leakage path**, not proof of positive displacement.
Discrete checks do not prove all-angle motion or loaded deflection.

## Hydraulic and fabrication issues before an operating build

- **Leakage:** tip gaps, two face gaps, backlash and shaft/bore clearances all
  bypass useful displacement. The pinned rotor bores use the shared gear clearance and
  are not shaft seals. Round lands pass through the journal/seal interfaces;
  D flats start outside both housing faces, avoiding a flat across a round seal. Housing journals and outboard counterbores are only
  bearing/seal interfaces. The 7 mm diameter, 1 mm deep seal reservations do
  not correspond to a selected commercial seal; redesign them around actual
  seal and bearing parts. The 8 mm OD removable collars bridge the 7 mm seal pockets; 0.05 mm
  collar-to-case gaps are smaller than the 0.10 mm rotor face gaps, so nominal
  collar stops precede rotor-face contact. Removable collars on both ends constrain the concept
  but set screws, axial load, flat fit and wear still need engineering.
- **Trapped volume:** more than one tooth pair may enclose a changing pocket.
  No timed face-relief grooves or transient fluid model are supplied. An external
  relief valve cannot necessarily relieve a pocket isolated between teeth.
  Before loaded operation, establish mesh pocket volume versus angle, then
  time a replaceable port/face plate to communicate a shrinking pocket to the
  appropriate side without bridging inlet and outlet. Do not cut an arbitrary
  cross-groove. Low-speed, freely discharging bench trials are the initial gate.
- **Porting:** circular side drillings reach the figure-eight cavity and the
  adjacent pocket, but inlet loss, filling, cavitation and outlet ripple are
  unmeasured. The nine downstream 0.4 mm holes provide only about 1.13 mm² open
  area versus a 7.07 mm² tube; substantial restriction/clogging is possible.
  Replace with a characterized, larger-area serviceable medium after flow tests.
- **Manufacturing:** gear profiles are reusable geometry, not validated pump
  cutters. Twelve teeth and the existing profile/root construction need contact,
  tip/root finish and undercut review. Flat faces require controlled machining
  or lapping; cast shrinkage, runout and swelling can consume these gaps. Cast
  the body as an open cavity, drill side ports/journals, and machine datum faces;
  a flat removable cover avoids a trapped cavity core. Rotor pin slots/holes, tooth
  release, journal coaxiality and collar set-screw pilots need fixtures/finishing.
  Use purchased metal shafts/bearings for the first hydraulic experiment.
- **Sealing/assembly:** select face gasket or O-ring groove, four clamp bolts,
  two engine bolts, bearing liners, dynamic shaft seals, filter cap fastening,
  insert retention and hose fittings before fabrication release. These are not
  silently counted as installed. For assembly, fit rotor/pin to each shaft,
  lower the pair into the open body with rear collars removed, slide on the
  cover, then install outboard collars. This removes the shoulder/gear trap;
  tool access, pin insertion and the actual installation sequence still need a
  physical trial. The engine pan still has open shaft exits,
  rail clearances, drain and service holes: the engine itself is not a sealed
  test reservoir. Test the pump separately first.
- **Materials:** pick oil and documented compatible resin, seals, metals and
  adhesives. Test immersed coupons for swelling, softening and cracking. No
  transparent casting, printability, friction pair or pressure containment is
  qualified by this model.

Clearance leakage and changing trapped tooth-space volume are established design
concerns, rather than an assurance that these particular dimensions work; see
[Yang et al., volumetric efficiency and dynamic clearances](https://www.mdpi.com/2076-0825/15/1/56).
That research does not validate this prototype.

## Bench protocol and measurable acceptance gates

These are proposed experiment gates, **not a pressure rating or test results**.
Record actual parts/materials, measured clearances, oil, temperature, speed,
torque/current, inlet/outlet pressure, collected mass and elapsed time.

1. Finish/seal the standalone unit and install a calibrated, independently rated
   relief valve, instrumented discharge and guarded torque-limited drive. Select
   the maximum permitted pressure from the weakest qualified hardware/fixture;
   this CAD supplies no allowable pressure. Resolve trapped-pocket relief before
   imposing back pressure. Verify valve opening/return separately with its
   manufacturer's procedure. Do not test by deliberately dead-heading this pump.
2. Measure journals, flatness, center distance, face/tip gaps and gear runout.
   Reject contact or negative running clearance at any angle. Turn ten full
   revolutions by hand with the intended lubricant: no binding or new scoring.
   Measure torque rather than calling a visually free mesh low-friction.
3. At ambient temperature, use a 100 mm oil head (a preliminary low-head
   leak-screen, not a proof-pressure test). After ten minutes require no visible
   external drops and less than 0.1 g unexplained mass loss, using a scale with
   adequate resolution. Check evaporation/control-container loss. Failure means
   repair/retest, not increased speed. Qualify resin coupons separately first.
4. With an unrestricted return and flooded inlet, trial 30, 60 and 120 **pump**
   rpm (crank 36.7, 73.3, 146.7 rpm). Collect for 60 s three times at each speed.
   Require repeatable positive net delivery in the predicted direction,
   repeatability within 10%, and volume/revolution within 20% across this range.
   Record outlet pressure and torque. These provisional criteria may reveal that
   the present gaps are too leaky; passing does not establish engine oil demand.
5. Repeat with the strainer, measure its pressure drop, and inspect debris.
   Require no contact, increasing torque trend or temperature rise exceeding
   10 °C during a ten-minute freely returning run. Stop on binding, leak, air
   ingestion, pressure excursion, cracking or rapid heating; identify cause.
   Measure actual volumetric efficiency only after a defensible displacement
   calculation/measurement and leakage characterization exist.
6. Only after seals, relief and trapped-volume treatment are qualified, make a
   controlled pressure/flow map below the selected fixture limit. Establish an
   engine-demand target experimentally: observe all six outlets and adequate
   return without flooding, then measure delivered flow and temperature in the
   actual assembled engine. Do not infer bearing lubrication from jet direction.

## Reproduce the review

In the repository's Docker/Poetry environment (or supported local Python 3.12 venv):

```sh
poetry run pytest tests/test_gear_pump.py
PYTHONPATH=. poetry run python scripts/render_gear_pump.py --output-dir previews/gear-pump
./run_checks.sh
```

Views use Efficio CAD tessellation, its raster preview and inspection clipping.
Pillow adds review labels and exploded offsets. Clear pan/jacket edges are an
outline convention, not transparency or a fluid simulation. Cutaways change only
the displayed copies. The JSON records actual solids, BOM and interference results.
