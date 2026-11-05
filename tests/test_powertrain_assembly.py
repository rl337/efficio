import csv
import os
import tempfile
import unittest

from efficio.__main__ import fetch_object_data
from efficio.examples.drivetrain import RearTransaxle, engine_assembly, rear_transaxle
from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.powertrain.engine import EngineGeometry
from efficio.objects.powertrain.fits import Process
from efficio.objects.powertrain.gears import SpurGear, mesh_phase
from efficio.objects.powertrain.layout import DrivetrainLayout


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
        self.assertEqual(quantities["crank_web"], 4)
        self.assertEqual(quantities["piston"], 2)
        self.assertEqual(quantities["connecting_rod"], 2)
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
        layout = DrivetrainLayout(
            engine=EngineGeometry(cylinders=1),
            crank_pinion_teeth=14,
            idler_gear_teeth=34,
        )
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
        shape = RearTransaxle(crank_angle=0.0, cylinders=2).shape()
        assert shape is not None
        bounds = shape.bounds()
        assert bounds is not None
        layout = DrivetrainLayout()
        self.assertAlmostEqual(bounds[2], 0.0, delta=0.3)
        self.assertAlmostEqual(bounds[1], layout.left_wheel.start, delta=0.5)
        self.assertAlmostEqual(bounds[4], layout.right_wheel.end, delta=0.5)
        self.assertGreater(
            bounds[5], layout.crank_centre[1] + layout.engine.deck_height
        )
