"""Geometric support preservation and motion checks for the toy proposal."""

from dataclasses import replace
from typing import Any

import cadquery as cq
import pytest

from efficio.examples.drivetrain import engine_assembly, rear_transaxle
from efficio.examples.open_engine import demonstration_layout
from efficio.objects.powertrain.engine import (
    CylinderHead,
    EngineBlockHalf,
    EngineGeometry,
)
from efficio.objects.profiles import box, cylinder


@pytest.mark.parametrize("bore,spacing", [(22.0, 30.0), (30.0, 40.0)])
def test_windows_remove_material_but_keep_supports(bore: float, spacing: float) -> None:
    e = replace(
        EngineGeometry() if bore == 22 else demonstration_layout().engine,
        cylinders=1,
        bore=bore,
        cylinder_spacing=spacing,
        windowed_block=True,
        window_width_fraction=0.45 if bore == 22 else 0.6,
    )
    assert e.problems() == []
    closed = replace(e, windowed_block=False)
    for upper in (True, False):
        opened = EngineBlockHalf(e, upper).shape()
        original = EngineBlockHalf(closed, upper).shape()
        assert opened is not None and original is not None
        a, b = opened.workplane().val(), original.workplane().val()
        assert isinstance(a, cq.Shape) and isinstance(b, cq.Shape)
        assert a.isValid() and len(a.Solids()) == 1
        assert a.Volume() < b.Volume()
        hw = e.block_half_width
        # End walls (including bearing seats, split bolts and optional flange)
        # and side-mount bridge retain exactly their original material.
        regions = [
            box(-hw - 1, hw + 1, y0, y1, -hw - 1, e.deck_height + 1).val()
            for y0, y1 in [
                (0, e.end_wall),
                (e.block_length - e.end_wall, e.block_length),
            ]
        ]
        regions.append(
            box(
                -hw - 1,
                hw + 1,
                0,
                e.block_length,
                e.side_mount_height - e.mount_bridge_height / 2,
                e.side_mount_height + e.mount_bridge_height / 2,
            ).val()
        )
        for region in regions:
            assert isinstance(region, cq.Shape)
            assert b.intersect(region).Volume() == pytest.approx(
                a.intersect(region).Volume(), abs=1e-6
            )
        for y0, y1, z0, z1 in e.block_windows():
            window = box(-hw - 1, hw + 1, y0, y1, z0, z1).val()
            assert isinstance(window, cq.Shape)
            assert a.intersect(window).Volume() < 1e-6
    head = CylinderHead(e).shape()
    assert head is not None
    h = head.workplane().val()
    assert isinstance(h, cq.Shape)
    assert h.isValid() and len(h.Solids()) == 1
    aperture = cylinder(e.bore / 2 - 0.1, 0, e.head_thickness, 0, e.cylinder_y(0)).val()
    assert isinstance(aperture, cq.Shape)
    assert h.intersect(aperture).Volume() < 1e-6


@pytest.mark.parametrize(
    "changes",
    [
        {"window_width_fraction": 1.0},
        {"window_width_fraction": float("nan")},
        {"window_width_fraction": 0.9},
        {"frame_rail": 30.0},
        {"frame_rail": -1.0},
        {"mount_bridge_height": 1.0},
    ],
)
def test_invalid_window_dimensions_are_reported(changes: dict[str, Any]) -> None:
    assert replace(demonstration_layout().engine, **changes).problems()


def test_neutral_default_and_unmounted_variant() -> None:
    assert EngineGeometry().block_windows() == []
    assert EngineGeometry(windowed_block=True).problems() == []
    e = replace(demonstration_layout().engine, side_mounts=False)
    assert e.problems() == []
    assert len(e.block_windows()) == e.cylinders * 2


def test_proposal_engine_motion_and_complete_drivetrain() -> None:
    layout = demonstration_layout()
    assert layout.problems() == []  # Includes analytical rod sweep at 5 degree steps.
    for angle in (0.0, 90.0, 180.0, 270.0):
        assert engine_assembly(layout, angle).interferences() == []
    assembly = rear_transaxle(layout, 30.0)
    assert assembly.interferences() == []
    assert assembly.quantities()["piston"] == 4
    assert len(assembly.find("Engine").children) == 8
