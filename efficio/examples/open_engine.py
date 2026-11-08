"""Editable larger-bore toy engine proposal; no combustion or strength claim."""

from efficio.objects.powertrain.engine import EngineGeometry
from efficio.objects.powertrain.layout import DrivetrainLayout


def demonstration_layout() -> DrivetrainLayout:
    """Concrete review dimensions live here; generic engine defaults stay intact."""
    return DrivetrainLayout(
        engine=EngineGeometry(
            bore=30.0,
            stroke=26.0,
            rod_length=52.0,
            cylinder_spacing=40.0,
            windowed_block=True,
            window_width_fraction=0.6,
            frame_rail=4.0,
            mount_bridge_height=8.0,
        )
    )
