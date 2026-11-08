"""Ownership, identity and quantity regressions for physical review groups."""

from collections import Counter

import pytest

from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.fits import Process
from efficio.objects.primitives import Box


def part(name: str = "rim") -> PartSpec:
    return PartSpec(
        name,
        Box(Millimeter(2), Millimeter(3), Millimeter(4)),
        (Process.FDM_PRINT,),
        "PETG",
    )


def test_repeated_child_parts_have_local_and_rolled_up_quantities() -> None:
    wheels = Assembly("Wheels")
    rim = part()
    first = wheels.place_world(rim, "rim_left", 1, 2, 3)
    second = wheels.place_world(rim, "rim_right", 1, 12, 3)
    originals = [first.solid, second.solid]
    left = wheels.group_instances("Left wheel", ["rim_left"])
    right = wheels.group_instances("Right wheel", ["rim_right"])
    left.add_hardware("retention screw", 1)
    right.add_hardware("retention screw", 1)
    assert not wheels.instances and not wheels.parts
    assert left.instances[0].solid is originals[0]
    assert right.instances[0].solid is originals[1]
    assert first.owner is left and second.owner is right
    assert wheels.quantities() == {"rim": 2}
    assert [r["quantity"] for r in wheels.bom_rows() if r["item"] == "rim"] == [
        "1",
        "1",
    ]
    assert {r["item"]: r["quantity"] for r in wheels.bom_totals()} == {
        "rim": "2",
        "retention screw": "2",
    }
    assert len(wheels.all_parts()) == 1


def test_grouping_errors_do_not_move_occurrences() -> None:
    root = Assembly("root")
    root.place_world(part(), "rim", 0, 0, 0)
    for labels in (["missing"], ["rim", "rim"]):
        with pytest.raises(ValueError):
            root.group_instances("invalid", labels)
    assert len(root.instances) == 1 and root.children == []
    with pytest.raises(ValueError, match="Conflicting"):
        root.register(part())
    child = root.group_instances("child", ["rim"])
    with pytest.raises(ValueError, match="Duplicate child"):
        root.add_subassembly(Assembly("child"))
    with pytest.raises(ValueError, match="cycles"):
        child.add_subassembly(root)


def test_paired_group_validation_precedes_changes() -> None:
    from efficio.examples.drivetrain_groups import group_sides

    root = Assembly("Wheels")
    root.place_world(part(), "rim_left", 0, 0, 0)
    with pytest.raises(ValueError, match="color"):
        group_sides(root, "wheel", [])
    root.add_hardware("retention screw", 1)
    with pytest.raises(ValueError, match="divide"):
        group_sides(root, "wheel", [(1, 2, 3), (4, 5, 6)])
    assert len(root.instances) == 1 and root.children == []
    assert root.hardware[0].quantity == 1


def test_ambiguous_names_require_paths_and_conflicting_parts_rejected() -> None:
    root = Assembly("root")
    shared = part()
    for side in ("left", "right"):
        group = root.add_subassembly(Assembly(side))
        nested = group.add_subassembly(Assembly("wheel"))
        nested.place_world(shared, "rim", 0, 0, 0)
    with pytest.raises(ValueError, match="Ambiguous"):
        root.find("wheel")
    with pytest.raises(ValueError, match="Ambiguous"):
        root.instance("rim")
    assert root.find("root / left / wheel").name == "wheel"
    assert (
        root.instance("root / right / wheel / rim").owner.path()
        == "root / right / wheel"
    )
    other = root.add_subassembly(Assembly("other"))
    other.place_world(part(), "other_rim", 0, 0, 0)
    with pytest.raises(ValueError, match="used twice"):
        root.bom_totals()


def test_gearbox_partition_preserves_solids_and_hardware() -> None:
    from efficio.examples.drivetrain import add_gearbox
    from efficio.examples.drivetrain_groups import group_gearbox
    from efficio.objects.powertrain.layout import DrivetrainLayout

    root = Assembly("Gearbox")
    add_gearbox(root, DrivetrainLayout(), 30)
    before = {p.label: p.solid for p in root.all_instances()}
    quantities = root.quantities()
    hardware = Counter((h.name, h.quantity, h.notes) for h in root.hardware)
    group_gearbox(root)
    assert root.quantities() == quantities
    assert (
        Counter((h.name, h.quantity, h.notes) for a in root.walk() for h in a.hardware)
        == hardware
    )
    assert all(p.solid is before[p.label] for p in root.all_instances())
    assert not root.instances and not root.hardware
    assert root.find("Engine output adapter").quantities() == {"crank_pinion": 1}
    assert root.find("Engine output adapter").hardware == []
    assert any(
        h.notes == "Carrier hubs in gearbox plates"
        for h in root.find("Gearbox support").hardware
    )
