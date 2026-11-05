import csv
import os
import tempfile
import unittest

import cadquery as cq

from efficio import renderer
from efficio.__main__ import fetch_object_data
from efficio.__main__ import main as efficio_main
from efficio.examples.drivetrain import (
    DIFFERENTIAL_COLOR,
    ENGINE_COLOR,
    GEARBOX_COLOR,
    TIRE_COLOR,
    WHEELS_COLOR,
    RearTransaxle,
    TransaxleSection,
    engine_assembly,
    gearbox_assembly,
    rear_transaxle,
)
from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.powertrain.engine import EngineGeometry
from efficio.objects.powertrain.fits import Process
from efficio.objects.powertrain.gears import SpurGear, mesh_phase
from efficio.objects.powertrain.layout import AxleStock, DrivetrainLayout


class TestDrivetrainAssembly(unittest.TestCase):
    layout: DrivetrainLayout
    assembly: Assembly

    @classmethod
    def setUpClass(cls) -> None:
        cls.layout = DrivetrainLayout()
        cls.assembly = rear_transaxle(cls.layout, crank_angle=0.0)

    def test_assembled_drivetrain_has_no_interference(self) -> None:
        self.assertEqual(self.assembly.interferences(), [])

    def test_part_counts(self) -> None:
        quantities = self.assembly.quantities()
        self.assertEqual(quantities["diff_planet_gear"], 4)
        self.assertEqual(quantities["diff_sun_gear"], 2)
        self.assertEqual(quantities["crank_web"], 8)
        self.assertEqual(quantities["piston"], 4)
        self.assertEqual(quantities["connecting_rod"], 4)
        self.assertEqual(quantities["engine_mount_left"], 2)
        self.assertEqual(quantities["crown_gear"], 1)
        self.assertEqual(quantities["idler_gear"], 1)
        self.assertEqual(quantities["wheel_rim"], 2)
        self.assertEqual(quantities["wheel_tire"], 2)
        self.assertEqual(quantities["gearbox_standoff"], 4)
        self.assertEqual(quantities["axle_pillow_block"], 2)

    def test_every_part_has_a_process(self) -> None:
        for spec in self.assembly.parts.values():
            self.assertTrue(spec.processes, spec.name)
            self.assertTrue(spec.material, spec.name)

    def test_wheels_touch_the_ground(self) -> None:
        tire = self.assembly.instance("wheel_tire_right").solid.BoundingBox()
        self.assertAlmostEqual(tire.zmin, 0.0, delta=0.3)
        head = self.assembly.instance("cylinder_head").solid.BoundingBox()
        self.assertGreater(head.zmax, 100.0)

    def test_export_writes_kit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.assembly.export(directory, include_assembly=False)
            names = {os.path.basename(p) for p in paths}
            self.assertIn("crank_pinion.stl", names)
            self.assertIn("gearbox_plate_left.dxf", names)
            self.assertIn("crank_web.dxf", names)
            self.assertNotIn("idler_shaft.stl", names)
            for path in paths:
                self.assertGreater(os.path.getsize(path), 0, path)
            with open(os.path.join(directory, "bom.csv"), encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            items = {row["item"]: row for row in rows}
            self.assertEqual(items["diff_planet_gear"]["quantity"], "4")
            self.assertIn("6800 ball bearing", items)
            bolt = items["M3 x 35 socket cap screw (planet pin)"]
            self.assertEqual(bolt["kind"], "hardware")
            self.assertEqual(bolt["quantity"], "4")
            self.assertNotIn("diff_planet_pin", items)
            self.assertNotIn("M3 x 35 socket cap screw (planet pin).stl", names)
            self.assertEqual(items["half_shaft_left"]["process"], "rod_stock")
            with open(os.path.join(directory, "BOM.md"), encoding="utf-8") as fh:
                self.assertIn("| crank_pinion |", fh.read())


class TestEngineSweep(unittest.TestCase):
    def test_engine_turns_without_interference(self) -> None:
        layout = DrivetrainLayout()
        for angle in (35.0, 90.0, 160.0, 270.0):
            with self.subTest(crank_angle=angle):
                assembly = engine_assembly(layout, angle)
                self.assertEqual(assembly.interferences(), [])

    def test_other_engine_configurations_turn_freely(self) -> None:
        for engine in (EngineGeometry(cylinders=1), EngineGeometry(cylinders=3)):
            layout = DrivetrainLayout(engine=engine)
            for angle in (35.0, 200.0):
                with self.subTest(cylinders=engine.cylinders, crank_angle=angle):
                    assembly = engine_assembly(layout, angle)
                    self.assertEqual(assembly.interferences(), [])


class TestVariantDrivetrain(unittest.TestCase):
    def test_single_cylinder_transaxle_assembles_cleanly(self) -> None:
        layout = DrivetrainLayout(engine=EngineGeometry(cylinders=1))
        assembly = rear_transaxle(layout, crank_angle=17.0)
        self.assertEqual(assembly.quantities()["piston"], 1)
        self.assertEqual(assembly.interferences(), [])


class TestInterferenceDetection(unittest.TestCase):
    def _pair(self, driven_offset: float) -> Assembly:
        assembly = Assembly("mesh check")
        module = MetricModule.MODULE_1_5
        pinion = PartSpec(
            "pinion",
            SpurGear(module, 12, Millimeter(5), Millimeter(5), False),
            (Process.FDM_PRINT,),
            "PLA",
        )
        gear = PartSpec(
            "gear",
            SpurGear(
                module,
                36,
                Millimeter(5),
                Millimeter(5),
                False,
                PressureAngle.HIGH_TORQUE,
            ),
            (Process.FDM_PRINT,),
            "PLA",
        )
        phase = mesh_phase((0.0, 0.0), 0.0, 12, (36.0, 0.0), 36)
        assembly.place_axial(pinion, "pinion", 0.0, 0.0, 0.0, True, 0.0)
        assembly.place_axial(gear, "gear", 36.0, 0.0, 0.0, True, phase + driven_offset)
        return assembly

    def test_phased_gears_clear(self) -> None:
        self.assertEqual(self._pair(0.0).interferences(), [])

    def test_mis_phased_gears_collide(self) -> None:
        collisions = self._pair(5.0).interferences()
        self.assertEqual(len(collisions), 1)
        self.assertGreater(collisions[0][2], 1.0)


class TestRearTransaxleObject(unittest.TestCase):
    def test_cli_discovers_composite_object(self) -> None:
        options = {cls.__name__: params for cls, params in fetch_object_data().items()}
        self.assertIn("RearTransaxle", options)
        self.assertEqual(options["RearTransaxle"]["crank_angle"][0], "float")
        self.assertEqual(options["RearTransaxle"]["cylinders"][0], "int")
        self.assertIn("BearingPlate", options)
        self.assertIn("SpurGear", options)

    def test_composite_shape_spans_the_build(self) -> None:
        shape = RearTransaxle(crank_angle=0.0).shape()
        assert shape is not None
        bounds = shape.bounds()
        assert bounds is not None
        layout = DrivetrainLayout()
        self.assertAlmostEqual(bounds[2], 0.0, delta=0.3)
        self.assertAlmostEqual(bounds[1], layout.left_wheel.start, delta=0.5)
        self.assertAlmostEqual(bounds[4], layout.right_wheel.end, delta=0.5)
        self.assertGreater(bounds[5], layout.crank_height + layout.engine.deck_height)


class TestDowelAxleTransaxle(unittest.TestCase):
    layout: DrivetrainLayout
    assembly: Assembly

    @classmethod
    def setUpClass(cls) -> None:
        cls.layout = DrivetrainLayout.with_dowel_axles()
        cls.assembly = rear_transaxle(cls.layout, crank_angle=40.0)

    def test_dowel_transaxle_has_no_interference(self) -> None:
        self.assertEqual(self.assembly.interferences(), [])

    def test_cross_pins_are_placed_across_the_axle(self) -> None:
        quantities = self.assembly.quantities()
        self.assertEqual(quantities["axle_cross_pin"], 4)
        pin = self.assembly.instance("axle_cross_pin_wheel_right").solid.BoundingBox()
        y = self.layout.axle_cross_pins()["wheel_right"]
        self.assertAlmostEqual((pin.ymin + pin.ymax) / 2, y, delta=0.05)
        self.assertAlmostEqual(pin.ymax - pin.ymin, 2.0, delta=0.15)
        span = max(pin.xmax - pin.xmin, pin.zmax - pin.zmin)
        self.assertGreater(span, 0.6 * self.layout.cross_pin_length)

    def test_bom_lists_dowels_and_wood_screws(self) -> None:
        rows = {row["item"]: row for row in self.assembly.bom_rows()}
        shaft = rows["half_shaft_left"]
        self.assertEqual(shaft["process"], "dowel_stock")
        self.assertIn("Ace item 5980552", shaft["material"])
        self.assertIn("#4 x 1/2 in wood screw + washer", rows)
        self.assertIn("R4 ball bearing", rows)
        self.assertIn("6801 ball bearing", rows)
        self.assertNotIn("M3 x 10 socket cap screw + washer", rows)
        with tempfile.TemporaryDirectory() as directory:
            names = {
                os.path.basename(p)
                for p in self.assembly.export(directory, include_assembly=False)
            }
        self.assertNotIn("half_shaft_left.stl", names)
        self.assertIn("wheel_hex_adapter.stl", names)

    def test_cli_object_builds_dowel_variant(self) -> None:
        obj = RearTransaxle(0.0, 2, AxleStock.WOOD_DOWEL)
        self.assertTrue(obj.layout().dowel_axles)
        options = {cls.__name__: p for cls, p in fetch_object_data().items()}
        self.assertEqual(options["RearTransaxle"]["axle_stock"][0], "AxleStock")


class TestSubassemblies(unittest.TestCase):
    assembly: Assembly

    @classmethod
    def setUpClass(cls) -> None:
        cls.assembly = rear_transaxle(DrivetrainLayout(), crank_angle=0.0)

    def test_named_after_car_parts(self) -> None:
        names = [child.name for child in self.assembly.children]
        self.assertEqual(
            names, ["Engine", "Gearbox", "Differential", "Axles", "Wheels"]
        )
        self.assertEqual(
            [s.value for s in TransaxleSection if s is not TransaxleSection.ALL],
            names,
        )

    def test_gearbox_contents(self) -> None:
        gearbox = self.assembly.find("Gearbox")
        labels = {p.label for p in gearbox.all_instances()}
        self.assertIn("crank_pinion", labels)
        self.assertIn("idler_gear", labels)
        self.assertIn("crown_gear", labels)
        self.assertIn("gearbox_plate_left", labels)
        self.assertNotIn("diff_sun_left", labels)
        self.assertEqual(gearbox.path(), "Rear transaxle / Gearbox")
        with self.assertRaises(KeyError):
            self.assembly.find("Transmission")

    def test_instances_are_split_without_loss(self) -> None:
        total = sum(len(c.instances) for c in self.assembly.children)
        self.assertEqual(total, len(self.assembly.all_instances()))
        self.assertEqual(self.assembly.instances, [])

    def test_gearbox_builds_and_renders_on_its_own(self) -> None:
        gearbox = gearbox_assembly(DrivetrainLayout())
        self.assertIsNone(gearbox.parent)
        self.assertEqual(gearbox.interferences(), [])
        image = renderer.create_object_preview(gearbox)
        self.assertGreater(image.width, 0)

    def test_parts_inherit_their_assembly_colour(self) -> None:
        colours = {label: color for label, _, color in self.assembly.preview_parts()}
        self.assertEqual(colours["crank_pinion"], GEARBOX_COLOR)
        self.assertEqual(colours["piston_0"], ENGINE_COLOR)
        self.assertEqual(colours["diff_planet_P1.0"], DIFFERENTIAL_COLOR)
        self.assertEqual(colours["wheel_rim_left"], WHEELS_COLOR)
        # Part-level override wins over the assembly colour.
        self.assertEqual(colours["wheel_tire_left"], TIRE_COLOR)

    def test_legend_lists_subassemblies(self) -> None:
        legend = dict(self.assembly.preview_legend())
        self.assertEqual(legend["Gearbox"], GEARBOX_COLOR)
        self.assertEqual(len(legend), 5)
        self.assertEqual(
            self.assembly.find("Gearbox").preview_legend(), [("Gearbox", GEARBOX_COLOR)]
        )

    def test_bom_grouped_by_subassembly(self) -> None:
        rows = self.assembly.bom_rows()
        groups = {row["item"]: row["assembly"] for row in rows}
        self.assertEqual(groups["crank_pinion"], "Rear transaxle / Gearbox")
        self.assertEqual(groups["wheel_tire"], "Rear transaxle / Wheels")
        markdown = self.assembly.bom_markdown()
        self.assertIn("## Rear transaxle / Differential", markdown)

    def test_cli_renders_a_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            png = os.path.join(directory, "gearbox.png")
            efficio_main(
                "RearTransaxle", [("section", "GEARBOX")], png, None, "#336699"
            )
            self.assertGreater(os.path.getsize(png), 0)
        obj = RearTransaxle(section=TransaxleSection.DIFFERENTIAL)
        self.assertEqual(obj.assembly().name, "Differential")
        self.assertEqual(obj.preview_legend(), [("Differential", DIFFERENTIAL_COLOR)])


class TestPreviewColourInheritance(unittest.TestCase):
    def test_resolution_order(self) -> None:
        root = Assembly("root")
        child = root.add_subassembly(Assembly("child"))
        gear = SpurGear(
            MetricModule.MODULE_1_5, 12, Millimeter(5), Millimeter(5), False
        )
        spec = PartSpec("gear", gear, (Process.FDM_PRINT,), "PLA")
        child.place_axial(spec, "gear", 0.0, 0.0, 0.0, True)
        current = (1, 2, 3)
        # Nobody has a colour: the renderer's current colour is used.
        self.assertEqual(gear.resolved_preview_color(current), current)
        root.preview_color = (10, 20, 30)
        self.assertEqual(gear.resolved_preview_color(current), (10, 20, 30))
        child.preview_color = (40, 50, 60)
        self.assertEqual(child.preview_parts(current)[0][2], (40, 50, 60))
        gear.with_preview_color((70, 80, 90))
        self.assertEqual(root.preview_parts(current)[0][2], (70, 80, 90))

    def test_subassembly_has_one_parent(self) -> None:
        child = Assembly("child")
        Assembly("a").add_subassembly(child)
        with self.assertRaises(ValueError):
            Assembly("b").add_subassembly(child)


class TestRightAngleDrive(unittest.TestCase):
    def test_crown_and_pinion_mesh_as_the_crank_turns(self) -> None:
        layout = DrivetrainLayout()
        for angle in (0.0, 11.0, 23.0):
            with self.subTest(crank_angle=angle):
                gearbox = gearbox_assembly(layout, angle)
                self.assertEqual(gearbox.interferences(), [])

    def test_engine_and_gearbox_fit_together(self) -> None:
        layout = DrivetrainLayout()
        both = Assembly("engine + gearbox")
        both.add_subassembly(engine_assembly(layout, 7.0))
        both.add_subassembly(gearbox_assembly(layout, 7.0))
        self.assertEqual(both.interferences(), [])

    def test_mis_phased_crown_collides(self) -> None:
        layout = DrivetrainLayout()
        good = gearbox_assembly(layout, 0.0)
        pinion = good.instance("crank_pinion")
        crown = good.instance("crown_gear")
        self.assertLess(pinion.solid.intersect(crown.solid).Volume(), 0.05)
        half_pitch = 360.0 / layout.crown_teeth / 2
        nx, nz = layout.input_centre
        shifted = crown.solid.rotate(
            cq.Vector(nx, 0, nz), cq.Vector(nx, 1, nz), half_pitch
        )
        self.assertGreater(pinion.solid.intersect(shifted).Volume(), 1.0)
