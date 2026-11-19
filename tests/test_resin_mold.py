import math
import os
from pathlib import Path
from typing import Callable

import cadquery as cq
import pytest

import efficio.objects.games.chess.resin_mold as rm
from efficio.examples.stacking_chess import SetEntry, stacking_chess_set
from efficio.examples.stacking_chess_molds import (
    SILICONE_MARGIN,
    export_stacking_chess_mold_stls,
    mold_kit,
    stacking_chess_mold_kits,
)
from efficio.machines import BuildVolume, MachineProfile
from efficio.measures import Millimeter
from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.games.chess import (
    CottleDimensions,
    HoldDownDimensions,
    KeyDimensions,
    MasterSplitDimensions,
    ResinCylinder,
    ResinCylinderDimensions,
    ResinMasterAssembly,
    ResinMasterFunnel,
    ResinMoldPlan,
    ResinMoldSetup,
    ResinPieceCast,
    StylizedPawn,
)
from efficio.objects.games.chess.resin_geometry import (
    PRINTED_TOOLING_WALL_POLICY,
    RESIN_WALL_POLICY,
    SILICONE_WALL_POLICY,
)
from efficio.objects.games.chess.resin_mold import shape_of


def volume(wp: cq.Workplane) -> float:
    return float(shape_of(wp).Volume())


def overlap(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return volume(a.intersect(b))
    except Exception:  # empty intersection raises in some OCC builds
        return 0.0


# -- pure geometry -----------------------------------------------------------
def test_defaults_are_valid_and_match_the_prototype_numbers() -> None:
    plan = ResinMoldPlan()
    assert plan.problems() == []
    assert plan.body_height == 40.0
    assert plan.master_length == 56.0
    assert plan.mold_length == 64.0
    assert plan.spacer_length == 10.0
    assert (plan.screw_seat, plan.screw_tip, plan.screw_engagement) == (
        -29.0,
        -4.0,
        5.5,
    )
    assert plan.mount_points() == [(53.0, -8.0), (53.0, 8.0)]
    assert math.isclose(plan.resin.key.tip_size()[0], 25.4493, abs_tol=1e-3)


def test_hole_sizes_come_from_the_fastener_catalogue() -> None:
    h = HoldDownDimensions()
    assert h.tap_drill == MetricThread.M3.spec.tap_drill
    assert h.clearance_hole == MetricThread.M3.spec.clearance_hole
    assert math.isclose(h.counterbore_diameter, 5.9)
    m4 = HoldDownDimensions(fastener=MetricThread.M4)
    assert m4.tap_drill > h.tap_drill


@pytest.mark.parametrize(
    "bad",
    [
        lambda: KeyDimensions(width=30.0),
        lambda: KeyDimensions(taper_degrees=50.0),
        lambda: KeyDimensions(notch_depth=3.0),
        lambda: KeyDimensions(clearance=-0.1),
        lambda: ResinCylinderDimensions(radius=12.0),
        lambda: ResinCylinderDimensions(pin_height=2.0),
        lambda: MasterSplitDimensions(peg_width=20.0),
        lambda: MasterSplitDimensions(funnel_flare_degrees=70.0),
        lambda: HoldDownDimensions(pilot_depth=9.0),
        lambda: HoldDownDimensions(counterbore_depth=2.0),
        lambda: HoldDownDimensions(spot_diameter=3.0),
        lambda: CottleDimensions(recess_depth=9.0),
        lambda: CottleDimensions(pour_slot_x=5.0),
        lambda: CottleDimensions(frame_wall=0.0),
        lambda: ResinMoldPlan(piece_height=float("nan")),
        lambda: ResinMoldPlan(piece_base_radius=19.0),
    ],
)
def test_bad_dimensions_are_rejected(bad: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        bad()


def test_wall_policies_flag_thin_walls() -> None:
    thin = CottleDimensions(silicone_wall=5.0, pour_slot_x=-2.5, pour_slot_width=4.0)
    with pytest.raises(ValueError, match="silicone_over_crest"):
        ResinMoldPlan(cottle=thin)
    with pytest.raises(ValueError, match="frame_wall"):
        ResinMoldPlan(cottle=CottleDimensions(frame_wall=1.5))
    with pytest.raises(ValueError, match="resin_ring_around_base"):
        ResinMoldPlan(piece_base_radius=17.0)
    with pytest.raises(ValueError, match="plate_above_counterbore"):
        ResinMoldPlan(cottle=CottleDimensions(plate_thickness=8.0))


def test_wall_policies_declare_required_features_and_provisional_status() -> None:
    plan = ResinMoldPlan()
    for policy, measured in (
        (PRINTED_TOOLING_WALL_POLICY, plan.printed_wall_measurements()),
        (SILICONE_WALL_POLICY, plan.silicone_wall_measurements()),
        (RESIN_WALL_POLICY, plan.resin.wall_measurements(plan.piece_base_radius)),
    ):
        assert set(policy.required_features) == set(measured)
        assert "provisional" in policy.qualification
        assert policy.violations(measured) == []


def test_screw_that_bottoms_out_in_the_pilot_is_rejected() -> None:
    long_screw = HoldDownDimensions(screw_length=27.0)
    with pytest.raises(ValueError, match="screw_length"):
        ResinMoldPlan(hold_down=long_screw)
    short_screw = HoldDownDimensions(screw_length=21.0)
    with pytest.raises(ValueError, match="screw_length"):
        ResinMoldPlan(hold_down=short_screw)


def test_non_default_plan_sizes_follow_the_parameters() -> None:
    plan = ResinMoldPlan(
        piece_height=43.5,
        cottle=CottleDimensions(silicone_wall=10.0),
        resin=ResinCylinderDimensions(cover=4.0),
        hold_down=HoldDownDimensions(screw_length=27.0),
    )
    assert plan.body_height == 9.0 + 43.5 + 4.0
    assert plan.half_height == 29.0
    assert plan.mold_length == plan.master_length + 10.0
    assert plan.screw_length_window() == (26.0, 27.5)
    # the default window brackets the M3 x 25 used for the default plan
    low, high = ResinMoldPlan().screw_length_window()
    assert low <= 25.0 <= high
    with pytest.raises(ValueError, match="screw_length"):
        ResinMoldPlan(cottle=CottleDimensions(silicone_wall=10.0))


# -- solids ------------------------------------------------------------------
@pytest.fixture(scope="module")
def plan() -> ResinMoldPlan:
    return ResinMoldPlan()


def test_cast_cylinders_stack_aligned_and_flipped_but_not_quarter_turned(
    plan: ResinMoldPlan,
) -> None:
    body = rm.cast_body(plan)
    assert math.isclose(volume(body), 45162.247, rel_tol=1e-6)

    def upper_at(angle: float) -> cq.Workplane:
        turned = body.rotate((0, 0, 0), (0, 0, 1), angle)
        return turned.translate((0, 0, plan.body_height))

    assert overlap(body, upper_at(0)) == pytest.approx(0.0, abs=1e-3)
    assert overlap(body, upper_at(180)) == pytest.approx(0.0, abs=1e-3)
    assert overlap(body, upper_at(90)) == pytest.approx(748.39, rel=1e-3)


def test_assembled_master_matches_one_piece_except_joint_gaps(
    plan: ResinMoldPlan,
) -> None:
    one = rm.master(plan)
    assembled = rm.assembled_master(plan)
    assert volume(assembled.cut(one)) == pytest.approx(0.0, abs=1e-3)
    gap = volume(one.cut(assembled))
    assert 100 < gap < 250
    assert math.isclose(gap, 176.774, rel_tol=1e-4)


def test_spacer_length_per_piece_matches_the_set() -> None:
    expected = {
        "pawn": 9.84,
        "rook": 10.0,
        "knight": 17.69,
        "bishop": 23.6,
        "queen": 19.0,
        "king": 25.5,
    }
    for entry in stacking_chess_set():
        kit = mold_kit(entry)
        assert kit.plan.spacer_length == pytest.approx(expected[entry.name], abs=0.01)


def test_cottle_parts_do_not_collide(plan: ResinMoldPlan) -> None:
    master = rm.lying(rm.master(plan))
    block_a, block_b = rm.cottle_block_a(plan), rm.cottle_block_b(plan)
    frame, plate, lid = (
        rm.cottle_frame(plan),
        rm.cottle_plate(plan),
        rm.cottle_lid(plan),
    )
    assert overlap(block_a, master) == pytest.approx(0.0, abs=1e-3)
    flipped = master.rotate((0, 0, 0), (1, 0, 0), 180)
    assert overlap(block_b, flipped) == pytest.approx(0.0, abs=1e-3)
    for first, second in (
        (frame, block_a),
        (frame, plate),
        (block_a, plate),
        (lid, frame),
    ):
        assert overlap(first, second) == pytest.approx(0.0, abs=1e-3)


def test_screws_bite_the_master_and_clear_blocks_and_plate(plan: ResinMoldPlan) -> None:
    master = rm.lying(rm.master(plan))
    spec = MetricThread.M3.spec
    for index in (0, 1):
        screw = rm.hold_down_screw(plan, index)
        bite = overlap(screw, master)
        # shank minus the tap-drilled core, over the engaged length
        expected = math.pi * (spec.major_diameter**2 - spec.tap_drill**2) / 4 * 5.5
        assert bite == pytest.approx(expected, rel=1e-3)
        for part in (
            rm.cottle_block_a(plan),
            rm.cottle_block_b(plan),
            rm.cottle_plate(plan),
        ):
            assert overlap(screw, part) == pytest.approx(0.0, abs=1e-3)


def test_screw_heads_sit_in_the_plate_counterbore(plan: ResinMoldPlan) -> None:
    spec = MetricThread.M3.spec
    head_top = plan.screw_seat
    assert head_top - plan.plate_bottom == plan.hold_down.counterbore_depth
    assert plan.hold_down.counterbore_depth >= spec.head_height


def test_silicone_volume_and_lid_height(plan: ResinMoldPlan) -> None:
    assert rm.silicone_per_half_ml(plan) == pytest.approx(67.917, abs=0.01)
    lid = rm.cottle_lid(plan)
    box = shape_of(lid).BoundingBox()
    assert box.zmin == pytest.approx(plan.half_height - plan.cottle.lid_lip)
    assert box.zmax == pytest.approx(plan.half_height + plan.cottle.lid_thickness)


def test_registration_dimples_are_slightly_larger_than_bumps(
    plan: ResinMoldPlan,
) -> None:
    block_a = rm.cottle_block_a(plan)
    block_b = rm.cottle_block_b(plan)
    c = plan.cottle
    x, y = rm._registration_points(plan)[0]
    probe = cq.Workplane("XY").sphere(c.registration_radius).translate((x, y, 0))
    # block A carries the bump; B must be able to take it with clearance
    assert overlap(block_a, probe) > 0.0
    assert overlap(block_b, probe) == pytest.approx(0.0, abs=1e-3)


def test_funnel_prints_flare_down(plan: ResinMoldPlan) -> None:
    part = ResinMasterFunnel(plan)
    box = shape_of(part.print_solid()).BoundingBox()
    assert box.zmin == pytest.approx(0.0, abs=1e-6)
    tip_length, _ = plan.resin.key.tip_size()
    assert box.xlen == pytest.approx(
        plan.split.funnel_top_size(plan.resin)[0], abs=0.05
    )
    assert box.xlen > tip_length


# -- objects ---------------------------------------------------------------
def test_objects_build_from_a_valid_plan_only(plan: ResinMoldPlan) -> None:
    assert ResinCylinder(plan).shape() is not None
    with pytest.raises(ValueError):
        ResinMoldPlan(piece_height=-1.0)


def test_master_assembly_preview_has_four_coloured_parts(plan: ResinMoldPlan) -> None:
    assembly = ResinMasterAssembly(plan)
    parts = assembly.preview_parts((0, 0, 0))
    assert [name for name, _, _ in parts] == [
        "bottom cap",
        "spacer",
        "top cap",
        "funnel",
    ]
    assert len({color for _, _, color in parts}) == 4
    assert len(assembly.preview_legend((0, 0, 0))) == 4


def test_piece_cast_embeds_the_piece_in_the_cylinder() -> None:
    cast = ResinPieceCast(StylizedPawn())
    assert cast.plan.piece_height == pytest.approx(27.8443, abs=1e-3)
    resin = volume(cast.solid())
    piece = volume(cast._placed_piece())
    assert resin == pytest.approx(volume(rm.cast_body(cast.plan)) - piece, rel=1e-6)
    names = [name for name, _, _ in cast.preview_parts((0, 0, 0))]
    assert names == ["resin", "piece"]


@pytest.mark.parametrize("pour", ["A", "B"])
def test_mold_setup_previews_cut_the_cottle_open(
    plan: ResinMoldPlan, pour: str
) -> None:
    setup = ResinMoldSetup(plan, pour)
    parts = setup.preview_parts((0, 0, 0))
    # plate, frame, block and master, plus the one screw on the y > 0 side
    assert len(parts) == 5
    for name, solid, _ in parts:
        assert solid.BoundingBox().ymin >= -1e-6, name
    assert setup.shape() is not None


def test_mold_setup_rejects_unknown_pour(plan: ResinMoldPlan) -> None:
    with pytest.raises(ValueError):
        ResinMoldSetup(plan, "C")


# -- example kit -------------------------------------------------------------
def test_every_kit_fits_the_printer_and_lists_silicone() -> None:
    kits = stacking_chess_mold_kits()
    assert [k.piece for k in kits] == [
        "pawn",
        "rook",
        "knight",
        "bishop",
        "queen",
        "king",
    ]
    for kit in kits:
        assert kit.oversize() == []
        assert kit.silicone_to_mix_ml == pytest.approx(
            kit.silicone_ml * SILICONE_MARGIN
        )
        assert 60 < kit.silicone_ml < 90
        assert len(kit.parts) == 9


def test_oversize_parts_are_reported_and_block_export(tmp_path: Path) -> None:
    tiny = MachineProfile(
        "tiny", BuildVolume(Millimeter(50), Millimeter(50), Millimeter(50))
    )
    kit = mold_kit(stacking_chess_set()[1])
    assert kit.oversize(tiny)
    with pytest.raises(ValueError, match="exceeds"):
        export_stacking_chess_mold_stls(str(tmp_path), tiny)
    assert not os.listdir(tmp_path)


def test_export_writes_every_part(tmp_path: Path) -> None:
    written = export_stacking_chess_mold_stls(str(tmp_path))
    assert sum(len(paths) for paths in written.values()) == 54
    for paths in written.values():
        for path in paths:
            assert os.path.getsize(path) > 1000


def test_section_through_the_screw_axis_shows_the_screw(plan: ResinMoldPlan) -> None:
    setup = ResinMoldSetup(plan, "A", section_y=plan.hold_down.offset)
    names = [name for name, _, _ in setup.preview_parts((0, 0, 0))]
    assert "M3 screw 2" in names
    assert "M3 screw 1" not in names
