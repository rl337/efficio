import os
import re
import tempfile
import unittest

from efficio.inspection import (
    inspection_pages_for,
    section_solid,
    write_mold_inspection_pdf,
)
from efficio.measures import Millimeter
from efficio.objects.mold_tooling import CottlePurpose, MoldPolarity, MoldTooling
from efficio.objects.primitives import Box
from efficio.objects.vases import TriangularFlaskVase


def _pdf_page_count(path: str) -> int:
    with open(path, "rb") as handle:
        data = handle.read()
    # Count page objects; exclude the /Pages tree node.
    return len(re.findall(rb"/Type\s*/Page\b(?!\s*s)", data))


class TestInspection(unittest.TestCase):
    def test_section_solid_halfspace_reduces_extent_along_cut_axis(self) -> None:
        box = Box(Millimeter(40), Millimeter(20), Millimeter(10)).shape()
        assert box is not None
        sectioned = section_solid(box, axis="X", position="mid", mode="halfspace")
        self.assertTrue(sectioned.isValid())

        full = box.bounds()
        cut = sectioned.bounds()
        assert full is not None and cut is not None
        full_x = full[3] - full[0]
        cut_x = cut[3] - cut[0]
        self.assertLess(cut_x, full_x * 0.75)
        self.assertAlmostEqual(cut[4] - cut[1], full[4] - full[1], delta=0.2)
        self.assertAlmostEqual(cut[5] - cut[2], full[5] - full[2], delta=0.2)

    def test_section_solid_slab_keeps_thin_band(self) -> None:
        box = Box(Millimeter(40), Millimeter(20), Millimeter(10)).shape()
        assert box is not None
        slab = section_solid(
            box, axis="Z", position="mid", mode="slab", slab_thickness=2.0
        )
        self.assertTrue(slab.isValid())
        bounds = slab.bounds()
        assert bounds is not None
        self.assertLessEqual(bounds[5] - bounds[2], 2.2)

    def test_negative_pdf_has_cavity_section_pages(self) -> None:
        tooling = MoldTooling(
            master=Box(Millimeter(30), Millimeter(30), Millimeter(30)),
            polarity=MoldPolarity.NEGATIVE,
            purpose=CottlePurpose.BOTH,
        )
        pages = inspection_pages_for(tooling)
        titles = [page.title for page in pages]
        self.assertIn("Inspection summary (NEGATIVE)", titles)
        self.assertIn("Silicone section X", titles)
        self.assertIn("Silicone section Z", titles)
        self.assertIn("Exploded tooling board", titles)

        silicone = tooling.silicone_shape()
        sectioned = section_solid(silicone, axis="X")
        self.assertTrue(sectioned.isValid())
        # Half-space cut of a hollowed block should remain smaller in X.
        full = silicone.bounds()
        cut = sectioned.bounds()
        assert full is not None and cut is not None
        self.assertLess(cut[3] - cut[0], full[3] - full[0])

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "negative.pdf")
            write_mold_inspection_pdf(tooling, path)
            self.assertGreater(os.path.getsize(path), 1000)
            self.assertGreaterEqual(_pdf_page_count(path), 8)

    def test_positive_pdf_includes_master_witness_and_sections(self) -> None:
        tooling = MoldTooling(
            master=TriangularFlaskVase(
                width=Millimeter(40),
                height=Millimeter(60),
                depth=Millimeter(20),
                neck=Millimeter(12),
            ),
            polarity=MoldPolarity.POSITIVE,
            purpose=CottlePurpose.MOLD_SUPPORT,
            silicone_thickness=Millimeter(8),
        )
        pages = inspection_pages_for(tooling)
        titles = [page.title for page in pages]
        self.assertIn("Inspection summary (POSITIVE)", titles)
        self.assertIn("Master witness", titles)
        self.assertIn("Silicone section X", titles)
        self.assertIn("Master beside silicone section", titles)

        master = tooling.master.shape()
        assert master is not None
        master_bounds = master.bounds()
        silicone = tooling.silicone_shape()
        silicone_bounds = silicone.bounds()
        assert master_bounds is not None and silicone_bounds is not None
        master_x = master_bounds[3] - master_bounds[0]
        silicone_x = silicone_bounds[3] - silicone_bounds[0]
        self.assertGreater(silicone_x, master_x)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "positive.pdf")
            write_mold_inspection_pdf(tooling, path)
            self.assertGreater(os.path.getsize(path), 1000)
            self.assertGreaterEqual(_pdf_page_count(path), 8)


if __name__ == "__main__":
    unittest.main()
