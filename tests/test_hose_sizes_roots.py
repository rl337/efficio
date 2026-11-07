"""Named size semantics and added-root preservation/access checks."""

from dataclasses import replace

import cadquery as cq
import pytest

from efficio.examples.water_feature_pump import (
    water_feature_pump,
    water_hose_terminal,
    water_pump_dimensions,
)
from efficio.objects.connectors import CommonHoseSize, HoseBarb, HoseBarbDimensions


def test_inch_metric_and_airline_names_are_distinct() -> None:
    assert CommonHoseSize.INCH_3_16_ID.value.id_mm == 4.7625
    assert CommonHoseSize.METRIC_4_MM_ID.value.id_mm == 4
    assert CommonHoseSize.INCH_5_16_ID.value.id_mm == 7.9375
    assert CommonHoseSize.METRIC_8_MM_ID.value.id_mm == 8
    assert CommonHoseSize.DANNER_AIRLINE_3_16_ID.value.od_mm is None
    assert CommonHoseSize.TETRA_AH_4_6.value.od_mm == 6
    assert len(CommonHoseSize) == 13


@pytest.mark.parametrize("size", list(CommonHoseSize))
def test_all_presets_can_size_a_generic_connector(size: CommonHoseSize) -> None:
    dimensions = HoseBarbDimensions.from_size(
        size.value,
        bore_radius=0.5,
        minimum_wall=0.5,
        hose_wall=None if size.value.od_mm else 1.0,
        length=15,
        barb_height=0.2,
        barb_length=2,
        barb_starts=(8, 11),
        hose_start=5,
        clamp_length=3,
        clamp_clearance=1,
        root_extra_radius=1,
        root_length=4,
    )
    assert dimensions.hose_id == size.value.id_mm
    assert 2 * dimensions.barb_radius == pytest.approx(size.value.id_mm + 0.4)
    shape = HoseBarb(dimensions).shape()
    assert shape is not None
    value = shape.workplane().val()
    assert isinstance(value, cq.Shape) and value.isValid() and len(value.Solids()) == 1


def test_pump_rejects_small_airlines_and_preserves_exact_selected_id() -> None:
    d = water_pump_dimensions()
    for size in (
        CommonHoseSize.METRIC_4_MM_ID,
        CommonHoseSize.TETRA_AH_4_6,
        CommonHoseSize.DANNER_AIRLINE_3_16_ID,
        CommonHoseSize.INCH_5_16_ID,
    ):
        with pytest.raises(ValueError, match="wall"):
            water_hose_terminal(d, size)
    assert water_hose_terminal(d, CommonHoseSize.METRIC_8_MM_ID).hose_id == 8
    assert water_hose_terminal(d, CommonHoseSize.INCH_3_8_ID).hose_id == 9.525


def test_supported_root_adds_only_material_and_preserves_other_parts() -> None:
    before = {
        n: s for n, s, _ in water_feature_pump(supported_roots=False).preview_parts()
    }
    after = {n: s for n, s, _ in water_feature_pump().preview_parts()}
    for name, old in before.items():
        new = after[name]
        if name == "water_body":
            assert old.cut(new).Volume() < 1e-6
            addition = new.cut(old)
            assert addition.Volume() > 1
            assert (
                addition.BoundingBox().zmax
                <= water_pump_dimensions().pump.depth - 0.05 + 1e-6
            )
        else:
            assert old.cut(new).Volume() + new.cut(old).Volume() < 1e-6


def test_root_profile_invalid_overlap_and_bore_clearance() -> None:
    h = water_hose_terminal(water_pump_dimensions())
    with pytest.raises(ValueError):
        replace(h, root_length=9.1)
    with pytest.raises(ValueError):
        replace(h, root_radius=3)
    root = HoseBarb(h).root_envelope()
    assert root is not None and root.isValid()
    plain = HoseBarb(replace(h, root_radius=0, root_length=0)).envelope()
    supported = HoseBarb(h).envelope()
    assert plain.cut(supported).Volume() < 1e-7
    assert h.finished_wall == 2


@pytest.mark.parametrize(
    "size", [CommonHoseSize.INCH_3_8_ID, CommonHoseSize.METRIC_12_MM_ID]
)
def test_larger_named_pump_variants_clear_cover(size: CommonHoseSize) -> None:
    parts = water_feature_pump(hose_size=size).preview_parts()
    assert all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in parts)
    for i, (name, a, _) in enumerate(parts):
        for other_name, b, _ in parts[i + 1 :]:
            assert a.intersect(b).Volume() < 1e-6, (name, other_name)
    d = water_pump_dimensions(hose_size=size)
    assert d.pump.port_drop > 0.3
    with pytest.raises(ValueError, match="taller chamber"):
        water_feature_pump(hose_size=CommonHoseSize.INCH_1_2_ID)
