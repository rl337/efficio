# Standalone water-feature gear pump experiment

This side project is independent of the engine oil circuit. Build the editable
wet end with `efficio.examples.water_feature_pump.water_feature_pump(angle)`.
`water_pump_dimensions()` is the concrete parameter entry point; shared
`BlindSupportPart` and `BlindSupportDimensions` are reusable. Shared involute
SpurGear and cross-pin geometry supply both rotors. There is no engine import.

This is a machining / assembly prototype with specific completion gates below,
**not an operational or fabrication-released water pump**. No measured water
flow, pressure, suction lift, endurance or resin compatibility exists yet.

## Provisional application and measurable goal

Assume a small indoor tabletop feature, clean room-temperature water, 100 mL/min
at 0.3 m static lift, initially 100–600 rpm. These are editable experimental
targets, not Richard's requirements or predicted performance. Start flooded,
with the reservoir surface above the inlet. No dry running or unattended duty.
A gear pump can have substantial leakage in water and is not presumed more
suitable than a purchased centrifugal fountain pump; this project tests that.

## Modeled parts and interfaces

- Capsule exterior 62.66 x 42.66 mm, case and cover total 24.16 mm thick.
  Figure-eight internal cavity is unchanged in principle: two 11.33 mm radius
  circles at 20 mm centers, with 11.25 mm gear tip radii.
- Two 16T, module 1.25, 25-degree pressure-angle involute rotors, 8 mm thick,
  backlash parameter 0.05 mm. 0.08 mm radial tip gap and 0.08 mm on each face.
- Both rotors are cross-pinned to rotating shafts. Two internal rear supports
  and the idler front support are blind. Only the driver exits the cover.
  Shaft CAD diameter 5.98 mm; journal diameter 6.08 mm (0.05 mm radial gap).
  Shared pinned rotor bore is 6.30 mm: its 0.16 mm radial shaft gap is a
  leakage and runout concern, not a precision hub fit. Correct with a qualified
  machined hub fit before claiming hydraulic performance.
- Rear blind wall and front idler blind wall are each 2 mm. Shaft ends have
  0.03 mm nominal gaps. These are not proven thrust bearings. Idler end stops
  precede its 0.08 mm rotor-face contact in ideal CAD; driver needs external
  axial restraint before running. Long metal shaft surface finishes and bore
  alignment need inspection. Resin bores are temporary journal geometry;
  replace / resize for qualified water-lubricated bushings before endurance.
- Four 3.3 mm clamp holes, 3.35 mm nominal inner/outer web at the circular
  ends. Use bolts, washers and nuts rather than threads directly in cast resin.
  Bolt length, gasket compression and torque await the chosen hardware.
- Separate capsule gasket envelope in a 0.3 mm deep, 1.5 mm wide recess,
  0.7 mm outside the wet cavity. It is shown at **installed thickness**;
  stock thickness, compression, material, sealing pressure and creep are TBD.
- One empty driver seal counterbore: 12 mm diameter x 4 mm depth, leaving
  4 mm of cover journal length. This is a provisional interface, NOT a
  selected catalogue seal or installed sealing lip. Do not order by dimensions
  alone. Supplier must approve water, speed, pressure, shaft finish, runout,
  mounting orientation and lubrication. Add positive seal retention if needed.
- Plain 4 mm inlet/outlet bores at x=10, z=12.08, y=+/-21.33. These are
  actual connected drilling paths, **not threaded fittings or hose barbs**.
  Opposing bores enter the central mesh pocket. At driver CCW viewed from +Z,
  +Y is inlet and -Y outlet; fluid travels around the outside of both gears.
  The gears do not provide an ideal seal through the central mesh or end gaps.
  No timed trapped-volume relief grooves have been designed or validated.

There are nine modeled occurrences: case, cover, gasket, driver and idler
shafts, two copies of one rotor identity, and two copies of one pin identity.
Hardware BOM explicitly identifies unselected clamp sets, rotary seal and
coupling/axial retention. No omitted motor is disguised as a fabricated part.

## Assembly and first physical build

1. Export STEP using `poetry run python scripts/render_water_feature_pump.py OUTPUT`.
   Finish-machine/lap faces, cavity and coaxial journal seats after casting;
   do not expect as-cast resin to hold the running clearances. Initially a
   machined body or transparent stock cover may reduce casting uncertainties.
2. Resolve water-rated shaft seal, bushings, hub fit and coupling/axial restraint.
   These are release blockers, not optional accessories. Reparameterize the
   seats to the actual supplier drawings. Use corrosion-resistant ground shafts
   with seal-compatible finish, no pin hole or flat crossing the lip's swept land.
3. Insert shafts into rotors, fit pins, then lower the paired rotating units into
   the open body. Pin insertion precedes lowering; pins do not require drilling
   through the housing. Trial assembly must verify retention and assembly access.
4. Install qualified gasket and cover over shafts, clamp evenly, then install
   seal and external retention/coupling according to their supplier procedures.
   Verify hand rotation over many revolutions before powering. Case faces may
   become thrust wear surfaces if axial restraint fails.
5. Fit positively retained water-compatible hose connectors at both plain ports.
   No glue-only pressure joint is assumed. Establish a removable, large-area
   screened pickup, submerged below minimum reservoir water level; no mesh or
   fitting geometry is yet modeled. Size/test screen for negligible restriction.

Candidate resin, elastomer and gear polymer require immersion/swelling, abrasion
and creep coupons with actual water additives, temperature and cure schedule.
No potable-water, aquarium, outdoor/UV or biological compatibility is claimed.
Straight axial draw of case and cover avoids internal casting undercuts, but
blind bores and side ports should be drilled/reamed after cure; gasket groove
and faces need finishing. Shrinkage allowances, bubbles, core/tool release,
minimum cast section and mold parting remain tooling work, not validated molds.

## Bench plumbing and motor isolation (not modeled system hardware)

Use a vented reservoir, short flooded suction hose and screened submerged
pickup. Outlet goes to a full-bore tee: one branch to a transparent adjustable
head riser with an always-open overflow back into the reservoir, the other to
flow collection. Initially all flow can use the open riser. Return must discharge
above the reservoir surface to observe flow; keep suction submerged. An open
standpipe is a bench head load, not a certified safety valve: friction, capacity
and overflow blockage can raise pressure. Do not close, kink or cap the outlet.
For a feature with a potentially blocked nozzle, select and verify a separate
low-pressure bypass/relief to reservoir, upstream of restriction, before use.
No relief valve, gauge, reservoir, screen or hose assembly is modeled here.

Use an externally mounted, guarded low-voltage motor with speed/current limits,
separate dry support and flexible coupling. Provide a drip-catching tray and an
open drainage gap between wet end and motor, not a sealed tunnel carrying leaked
water into the motor. Motor, coupling, bracket, guard and wiring remain to be
selected around measured torque and actual motor pattern. Keep mains equipment
away from splash, use a suitable certified isolated supply and GFCI protection,
and have the final installation checked for its location. Low voltage does not
make an unsealed motor submersible. This CAD has no electrical enclosure rating.

## Bench protocol and provisional acceptance gates

Record water temperature, RPM under load, supply current, head relative to inlet
free surface, external leak collection and flow. Hydrostatic fill before motor
power: inspect every joint and driver seal at 0.3 m water head for 15 minutes.
Reject any visible leak. Use guarded manual rotation and a torque-limited drive.

Measure at 100, 300 and 600 rpm and at 0, 0.1, 0.3 and 0.5 m head, progressively
only while current, temperature and leakage remain acceptable. Collect outlet
water for 60 seconds, three repeats per point; weigh it, convert using measured
water temperature/density, and report mean and spread. Capture speed so stalled
or slowed runs are not mislabeled. Weigh captured external leakage separately.
No-flow, persistent bubbles, binding, unexpected current rise or hot surfaces
mean stop and inspect; never compensate by closing the discharge.

Initial success gate: >=100 mL/min at 0.3 m at some recorded speed <=600 rpm,
no visible external leakage, repeatability within 10%, no tooth/pin/bearing damage.
Then 30 minutes continuous, inspect, and only then a supervised 2-hour trial:
flow drift <=10%, current drift <=20% from warmed baseline, wet-end temperature
<=40 C and <=10 C above water, captured external leakage <1 g (correct for
collection/evaporation error), no visible wear debris or new binding. These are
provisional experiment criteria, not continuous-duty certification. Failures
should drive clearance, hub, material or seal changes before longer operation.
Test restart/priming after stopping flooded; suction-lift testing is a separate
experiment. Do not claim self-priming from the gear topology.

Record pre/post shaft runout, journal diameters, face flatness and rotor endfloat.
A provisional machining gate is <=0.02 mm total indicated shaft runout and <=0.02
mm face flatness; supplier seal requirements and measured tolerance stack may be
tighter. Budget eccentricity, thermal change and swelling against the 0.08 mm
radial gap; CAD gaps alone are not a tolerance analysis.

## Source basis and next decisions

SKF's [seal analysis](https://evolution.skf.com/us/seal-analysis-pays/) identifies
lubrication, pressure, material compatibility and eccentricity as seal design
inputs; it does not qualify this proposed seat for water. Viking's
[external gear pump explanation](https://vikingpump.com/faq/how-do-external-gear-pumps-work)
supports the outside-tooth transport direction, not a performance estimate.
[OSHA fountain electrical provisions](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.306)
illustrate location-specific protection requirements; final residential/local
requirements need checking for the actual installation.

Needed for the next build revision: desired feature flow and lift, indoor/outdoor,
reservoir size and water additives, hours per day, noise preference, available
machining capability, and motor/power source. Select seal/bearings/coupling first;
then finish the dry mounting, fittings and relief system around actual parts.
