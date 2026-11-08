# Water-feature gear pump — resume here

Paused deliberately on 2026-11-08. The project is an editable CAD and bench-test
candidate, **not an operational, leak-tight or fabrication-released pump**.
The user paused the design work and subsequently requested integration into `main`.
This handoff does not authorize ordering components or future publication actions.

## Branch and source of truth

- Original review branch: `review/drivetrain-physical-groupings`. Resume from
  `main` after its integration PR; the review commits remain in history.
- Last implementation commit at handoff: `cd567b67d7dcef0c141833f1bf587ccca9a2e8ed`
  (generic gasket defaults). The handoff documentation is committed after it.
- Working checkout used here:
  `/Users/richard/Documents/Codex/2026-11-06/task/efficio-reconcile`.
- This branch also contains earlier drivetrain grouping, educational resin engine
  and lubrication work. Preserve it; do not replace the branch with only the pump.
- The review was local at the original pause. Richard subsequently explicitly
  authorized publishing and merging the complete branch into `main`; verify the
  integration PR and current remote head when resuming.

## Which model to reopen

| Entry point | Purpose and status |
|---|---|
| `efficio.examples.gasket_review.full_face_pump_review()` | **Latest face/gasket direction.** Returns the revised body and separate gasket design, not a complete installed pump assembly. Build its matching cover with `BlindSupportPart(body.d, "cover")`. |
| `scripts/render_full_face_gasket.py OUTPUT` | Recreates comparison, actual face/exploded view, residual-leakage view, seven STEP artifacts and measurements. |
| `efficio.examples.water_feature_pump.water_feature_pump(angle)` | Earlier complete nine-occurrence wet-end assembly, useful for reference/motion/BOM. It still has the earlier capsule gasket; it was deliberately not silently replaced. |
| `pump_gasket_review()` / `rectangular_gasket_review()` | Earlier wider oval review and independent generic flange example. Retained for comparison and tests. |
| `efficio.examples.pumped_engine.pumped_engine_assembly()` | Separate earlier crank-driven **oil** pump/lubrication review. Do not conflate its interfaces with the water project. See [oil-pump guide](external-gear-pump.md). |

The complete wet-end reference contains body, cover, gasket, two shafts, two
rotor occurrences and two cross-pin occurrences. Motor, coupling, qualified
seals/bushings and final retention hardware are not modeled as installed parts.

## Current water design and reusable pieces

The latest full-face variant keeps the 16-tooth, module-1.25 involute rotors,
20 mm centers, 8 mm gear width, figure-eight chamber and original cover plane.
It retains 0.08 mm tip and face clearances and a 0.05 mm backlash parameter.
These are CAD choices, not demonstrated machining or casting tolerances.

- **Housing:** organic exterior following the chamber, cylindrical bolt bosses,
  outer-end bevels, blind bottom journals, blind upper idler journal and one
  driver exit. Full-face variant has 10 mm exterior offset, 6 mm boss radius and
  the revised bolt pattern. Always use its matching cover.
- **Full-face gasket:** covers both nose/wedge regions and surrounds four explicit
  bolt openings. 0.7 mm hard lands remain at cavity, bolt holes and exterior.
  Free gasket has another 0.4 mm inset. The rounded construction provides a
  2 mm geometric width lower bound and reports removed tip/corner area.
  The actual review uses **1.05 mm free / 1 mm closed**, not the generic defaults.
  Its ports move down 0.7 mm to preserve the 2.08 mm roof below the deeper recess.
  See [full-face findings](full-face-pump-gasket.md).
- **Generic gasket API:** named planar faces, explicit opening identities and
  supplied keep-outs; separate free, installed-estimate, clearance and recess
  artifacts. Default minimum band is **1 mm**, common inset **0.4 mm**, free
  thickness **2 mm**, all configurable. Independent inner/outer overrides retain
  old positional calls. Caller selects the source face; no automatic two-part
  matching exists. Closed height remains deliberate and mandatory. A 2 mm free
  gasket overfills the current pump recess and is rejected. See [API](gasket-faces.md).
- **Reusable connectors:** `objects/connectors/` provides parameterized hose barbs,
  tapered root support and named metric/imperial hose-ID presets. Default water
  terminals target 8 mm hose ID, provisional 12 mm OD and a 4 mm bore. The
  supported root is 13 mm diameter over 8 mm length with a rounded neck. Hose
  fit, clamp retention and strength remain untested. Aquarium airline presets
  preserve literal 3/16 inch (4.7625 mm) versus 4 mm ID / 6 mm OD; they do not
  establish Tetra Whisper fit or water-service suitability. See [terminals](tube-terminals.md).
- **Reusable pump/gears:** `objects/pumps/{geometry,external_gear,blind_support}.py`
  use shared `SpurGear`/involute geometry rather than engine-specific tooth copies.
- **Material/process policy:** `objects/walls.py` separates finished-wall budgets
  from manufacturing allowances. Resin values are provisional; slip-cast ceramic
  remains explicitly unqualified for this wet end. See [wall policy](wall-policy.md).

## Precisely what is verified

At implementation commit `cd567b6`, Docker `bash run_checks.sh` completed with
**403 passed in 706.58 seconds**. MyPy passed 130 source files; Black and isort
passed. The targeted gasket run passed **26 tests in 22.04 seconds**. Coverage
was not measured because pytest-cov was unavailable; flake8 and bandit were also
unavailable. The script's print-statement scan falsely matches the name
`footprint`; that warning is not a test failure. No remote CI was run for these
unpublished commits.

Tests include defaults/overrides, exact width boundaries, invalid inputs,
explicit opening failures, unsupported/invalid geometry, narrow-waist rejection,
keep-outs, stop planes, pump incompatibility with the 2 mm default, nose coverage,
old-groove separation and six rotor positions. Broad regressions include existing
engine, drivetrain, BOM, mold tooling and CLI paths.

The full-face CAD views were visually inspected. All **seven STEP artifacts**
reimported valid; one artifact is a diagnostic fluid-gap slice, not a manufactured
part. A probe through the lowered side/terminal bore found **0 mm3 housing
obstruction**. These artifacts were generated at `77990c2`; the subsequent default
change preserves their explicitly configured geometry. Local raw validation logs
are outside the repo (`../gasket-default-final-checks.log`); the summary here is
retained in version control. The handoff itself is documentation-only and does
not claim another execution of the full suite.

## Known gaps and decisions — resume in this order

1. **Confirm the actual water feature.** Required flow/head, duty, reservoir level,
   suction arrangement, water additives/debris, environment, noise, footprint,
   power source and budget remain unspecified. The earlier 100 mL/min at 0.3 m,
   100–600 rpm, clean room-temperature water target is an experiment assumption,
   not the user's requirement or predicted performance.
2. **Resolve shaft support, retention and seal together before fabrication.** Both
   shafts currently rotate with their gears. Bottom sockets are blind, about
   6 mm deep with 2 mm floors. The idler has a roughly 6 mm blind upper socket;
   the driver has a through-journal with about 4 mm support below the seal seat.
   Shafts are 5.98 mm CAD diameter in 6.08 mm journals. These are provisional resin
   bore interfaces, not qualified bearings. Select water-compatible bushings,
   corrosion-resistant ground shafts and a controlled hub fit; current 6.30 mm
   rotor bores leave appreciable shaft clearance. Cross-pins in lower-face gear
   slots transmit torque but do not supply complete axial retention. Provide
   thrust/axial restraint; driver retention/coupling remains unselected. The
   driver has an **empty 12 mm x 4 mm seal seat**, not an installed waterproof
   seal. Select a water-qualified rotary seal for actual pressure, speed,
   lubrication, shaft finish/runout and service, then resize its seat and retention
   to supplier drawings. The flat gasket cannot seal the rotating shaft exit.
3. **Resolve hydraulic leakage experimentally and geometrically.** The old oval
   groove was separated from water by solid land; the old noses contacted the
   cover in ideal CAD. Full-face coverage improves the face interface but does
   not prove it seals. A connected **0.08 mm upper gear gap** remains across both
   port sides. Tip gaps, backlash, hub/journal paths, shaft sealing and trapped
   tooth volume are separate unresolved mechanisms. Do not remove running gaps
   or put silicone into the tooth swept envelope to hide these paths. Select
   end-face/bearing materials and tolerances, then measure flow versus head.
4. **Choose actual materials and a manufacturing route.** Resin grade/cure, gear
   polymer, silicone formulation/hardness, dimensional recovery, compression set,
   immersion swelling and repeated-use behavior are unqualified. Mold-making
   silicone is not automatically a validated gasket material. The spread estimate
   and its 1.25 multiplier are not a physical worst-case bound. Finish machining,
   face flatness, runout, endfloat, shaft finish and alignment must be measurable.
5. **Complete a controlled bench assembly.** Select motor, coupling, mounts/guard,
   shaft restraint, screen, plumbing, pressure/flow instrumentation and an open
   return/appropriate relief-bypass arrangement. No completed water-system
   relief/filter/screen assembly is modeled. Keep the motor/electrics isolated
   from water; select suitable certified supply/protection and installation for
   the actual location. This CAD has no electrical enclosure rating. Do not run
   dry, dead-head, or leave the prototype unattended.
6. **Test before claiming performance.** Follow the provisional [bench protocol](water-feature-pump.md#bench-protocol-and-provisional-acceptance-gates):
   material/fit coupons; hand rotation; unpowered hydrostatic leakage; separate
   suction/air-ingress checks; measured flow-versus-head/current/temperature;
   staged endurance; post-test wear/runout inspection; repeated gasket assembly.
   Its numerical gates are experimental, not a pressure or continuous-duty rating.
7. **Design mold/cottle tooling only after geometry and process stabilize.** No
   pump-specific casting mold, gasket mold, mother mold or cottle is generated
   or qualified. Resolve parting, release/draft, hose-barb/root undercuts, blind
   bores/cores, side drilling, gasket filling/venting/flash, shrinkage/cure and
   machining allowances. Existing generic gear/mold tooling tests do not certify
   tooling for this pump. Avoid committing to as-cast precision running clearances.
8. **Integrate the reviewed variant deliberately.** After the choices above,
   update the complete assembly/BOM with the matching body, cover, generated
   gasket and selected hardware; rerun motion, wall, passage, export and full
   regression checks. Retain comparison variants or explicitly retire them with
   evidence. Ask before publishing or merging.

## Resume commands and review files

Start with `git status`, current `main`, and this document. Preserve any
new work found later. Use the Docker or local-venv workflow in `AGENTS.md`; do
not install CAD dependencies into the global Python environment.

Inside the supported development environment, from the repository root:

```bash
PYTHONPATH=. poetry run python scripts/render_full_face_gasket.py /tmp/full-face-pump-review
poetry run pytest tests/test_gasket_defaults.py tests/test_gasket_faces.py tests/test_full_face_gasket.py tests/test_water_feature_pump.py
bash run_checks.sh
```

The existing local Docker container was `efficio-reconciliation`, with this
checkout at `/work/efficio-reconcile`. If it is no longer available, recreate the
supported environment rather than treating old container state as required.

Latest saved review artifacts (these are the full-face revision, not older oval views):

| Artifact | Library ID |
|---|---|
| `30-full-face-gasket-comparison.png` | `libfile_0fb0b2fc30f0819193558304ba19cf3a` |
| `31-full-face-declaration-and-exploded.png` | `libfile_4c3aafe4c29881919f9712f4e80e99a9` |
| `32-full-face-residual-leakage.png` | `libfile_b3d95573d6388191b109a01fdade38ed` |
| `full-face-gasket-review.zip` (images, STEP, measurements, then-current guides) | `libfile_d308c8cb202881919628af19f3d58ad6` |

Local originals are in `../full-face-gasket-review/`. The ZIP predates this
handoff and the latest defaults documentation; use repository docs as current
source. Rendering is Efficio tessellation/software rendering with Pillow labels,
not an optical, fluid or structural simulation. Reproduce artifacts from source
if the local files or Library copies are unavailable.

Suggested resumption request: **“Resume the water pump from
`docs/water-pump-handoff.md`; first confirm the feature requirements and select
the shaft, bushings, rotary seal and axial retention as a coordinated package.”**
