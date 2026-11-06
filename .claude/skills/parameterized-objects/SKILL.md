---
name: parameterized-objects
description: Use when adding or changing any efficio object (an EfficioObject subclass, part, fastener, gear or assembly). It requires objects to be defined by parameters in a categorized submodule, and made concrete only where a standard or a use site requires it.
---

# Parameterized object definitions

Every object in efficio is **defined by its parameters** and lives in a
**submodule named for what it is**. Values are fixed only when something
requires them to be. That is either a *standard* (which fixes what the standard
defines) or a *use site* (an assembly, example or test that needs one specific
part).

## The three levels of concreteness

Think of every object as moving from general to specific. Only go as far as you
need to.

| Level | What is fixed | Where it lives | Example |
| --- | --- | --- | --- |
| 1. Generic | nothing; every dimension is a parameter | the category submodule | `Bolt(thread, length, head)` |
| 2. Standard | exactly what the standard defines | a catalogue next to the generic class | `M3Bolt(length)`: thread pitch, major diameter, head size and drive fixed by ISO 4762, length still free |
| 3. Concrete | everything | only the use site that needs it | `M3Bolt(Millimeter(10))` in an assembly, example or test |

The M3 bolt illustrates the rule:

- A **bolt** is generic: thread, length and head are all parameters.
- An **M3 bolt** is a bolt with the M3 values fixed (pitch 0.5, 3 mm major
  diameter, 5.5 mm head, 3 mm head height), because the standard defines them.
  Its length is *not* part of being "M3", so it stays a parameter.
- An **M3 × 10 bolt** is fully concrete. Create it only where a 10 mm M3 bolt
  is actually used, never as a module-level object in the fastener module.

Apply the same reasoning everywhere. A `SpurGear` is generic; a module-1.5,
25° pressure-angle gear is a choice of standard values (`DrivetrainSpurGear`
fixes `DRIVETRAIN_GEAR_SYSTEM`); "the 12-tooth crank
pinion" exists only in the transaxle builder.

## Rules

1. **Define the generic object first.** Its constructor takes every dimension
   that could reasonably change. Derive everything else from those parameters.
   Do not leave magic numbers in the geometry: a hole offset, a wall thickness
   or a bolt pattern is either a parameter or computed from parameters.
2. **Express standards as catalogues, not copies.** Put standard values in an
   `Enum` of frozen dataclasses (see `StandardBearing`, `StandardDowel`,
   `MetricModule`) or a spec dataclass. The standard-level object takes the
   catalogue entry plus whatever the standard leaves open:
   - subclass that passes the fixed values to the generic constructor, or
   - a `from_<spec>()` / `for_<standard>()` classmethod or factory function
     (see `CrankWeb.from_engine`, `sun_gear(geometry)`).
   Never duplicate the generic geometry code for a standard size.
3. **Concrete instances belong at use sites only.** Assemblies, builders
   (`efficio/examples/`), tests and CLI invocations create fully concrete
   objects. Object modules must not define module-level concrete instances of
   parts. Catalogue *data* (standard dimensions) is fine; constructed parts are
   not.
4. **Put each object in a categorized submodule.** Choose the package by what
   the object *is*, not by the first project that needs it:
   - general gears: `efficio/objects/gears/` (standards, involute geometry,
     `SpurGear`, `CrownGear`, simple gears). Gears fixed to one project's gear
     system go in that project, e.g. `powertrain/gears` (`DrivetrainSpurGear`)
   - general helpers: `efficio/objects/{fits,profiles,planar}.py`
   - powertrain parts: `efficio/objects/powertrain/{engine,gearbox,differential,axles,wheels}`
   - shared powertrain building blocks: `powertrain/{shafts,bearings,dowels}`
   - fasteners, enclosures, molds and so on: a package for that category (for
     example `efficio/objects/fasteners/` for bolts, nuts and inserts)

   If no category fits, create one with an `__init__.py` that documents what
   belongs there and re-exports its public classes. Don't drop the class into
   whichever module happens to be open.
5. **Reuse existing parameterized pieces** before writing new geometry. Use
   `SpurGear` (hub, cross-pin drive), `Shaft` (round, D-flat, cross-drilled),
   `Standoff`, `BearingPlate`, `bearing_seat_cutter`, `bore_cutter`, the
   `profiles` helpers and the `planar` hull/convex helpers. If a new part
   is "an X with one extra feature", add that feature to X as a parameter
   with a neutral default.
6. **Keep pure geometry separate from solids.** Sizing, kinematics, meshing
   phases and clearance checks go in CadQuery-free modules (`*/geometry.py`,
   `involute.py`, `face.py`, `layout.py`). Give them a `problems()` method that
   reports violations, so they can be tested without building solids.
7. **Stay CLI-compatible.** `python -m efficio` discovers every `EfficioObject`
   and builds it from `--params`. Annotate constructor parameters with
   `Measure`, `int`, `float`, `bool`, `str` or an `Enum`. Complex specs (layouts,
   geometry dataclasses) are allowed for objects that need them, but provide
   defaults wherever a sensible one exists. Use parameter defaults rather than
   overloads.
8. **Leave colour to the hierarchy.** Don't set `preview_color` on ordinary
   parts. Sub-assemblies carry the colour; override a part only when its
   material is the point (tyres, wood).

## Checklist for a new or changed object

- [ ] Generic class with every reasonable dimension as a parameter, no magic
      numbers.
- [ ] Standard values in a catalogue (Enum/dataclass), with the source standard
      named in a comment.
- [ ] Standard-level variant fixes only what the standard defines.
- [ ] No module-level concrete parts; concrete sizes appear only in
      assemblies, examples or tests.
- [ ] Lives in the right category submodule, re-exported from its
      `__init__.py`.
- [ ] Reuses existing parameterized building blocks.
- [ ] Pure geometry and `problems()` separated from CadQuery code.
- [ ] Constructor annotations are CLI-friendly, with defaults where sensible.
- [ ] Tests build the object with at least one non-default parameter set as
      well as the standard one, and check `problems()` rejects bad values.

## Reference implementations

- `efficio/objects/fasteners/`: `MetricThread` catalogue (ISO 4762 / ISO 4032
  values), generic `Bolt`, `HexNut`, `BoltChannel`, and `M3Bolt(length)` etc.
  as the standard-level variants.
- `efficio/machines.py`: `StandardMachine` catalogue of build volumes.
- `efficio/objects/powertrain/engine/geometry.py`: every wall, inset and
  bolt depth is a field with the old literal as its default, and the bolt size
  is a `fastener: MetricThread` field.
