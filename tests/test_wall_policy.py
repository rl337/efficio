"""Project-specific finished-wall limits and separate process allowances."""

from dataclasses import replace

import pytest

from efficio.examples.water_feature_pump import (
    resin_water_profile,
    slip_cast_water_profile,
    water_pump_dimensions,
    water_wall_policy,
)
from efficio.objects.fits import Process
from efficio.objects.walls import MaterialWallProfile


def test_wall_policy_rejects_missing_and_thin_features() -> None:
    policy = water_wall_policy()
    measurements = water_pump_dimensions().wall_measurements()
    assert not policy.violations(measurements)
    assert policy.violations({})
    measurements["port_roof_to_joint"] = 1.99
    with pytest.raises(ValueError, match="port_roof"):
        policy.require(measurements)
    with pytest.raises(ValueError):
        replace(policy, minimum_mm=float("nan"))
    with pytest.raises(ValueError):
        replace(policy, material="")


def test_process_allowances_do_not_change_finished_wall_threshold() -> None:
    profile = resin_water_profile()
    with pytest.raises(ValueError, match="shrinkage"):
        profile.tool_dimension(10)
    # Arithmetic fixture only: 10% is not a measured material recommendation.
    fixture = replace(profile, linear_shrinkage=0.1, machining_allowance_mm=0.8)
    assert fixture.tool_dimension(10) == pytest.approx(12)
    assert fixture.finished_policy().minimum_mm == 2
    with pytest.raises(ValueError):
        replace(profile, linear_shrinkage=1)
    with pytest.raises(ValueError):
        replace(profile, machining_allowance_mm=-1)


def test_slip_cast_is_explicitly_unqualified() -> None:
    profile = slip_cast_water_profile()
    assert profile.process == Process.SLIP_CAST
    assert profile.policy is None and profile.linear_shrinkage is None
    with pytest.raises(ValueError, match="unqualified"):
        water_pump_dimensions(profile)
    with pytest.raises(ValueError, match="processes differ"):
        MaterialWallProfile("mismatch", Process.SLIP_CAST, water_wall_policy())


def test_material_profile_changes_finished_geometry() -> None:
    baseline = water_pump_dimensions()
    # Deliberately hypothetical resin budget: not a second qualified material.
    thicker = replace(
        resin_water_profile(), policy=replace(water_wall_policy(), minimum_mm=3)
    )
    variant = water_pump_dimensions(thicker)
    assert variant.exterior_offset > baseline.exterior_offset
    assert variant.boss_radius > baseline.boss_radius
    assert variant.back_web == 3
    assert variant.pump.width > baseline.pump.width
    thicker.finished_policy().require(variant.wall_measurements())
