from typing import TYPE_CHECKING, Optional, Tuple, TypeVar

from efficio.objects.shapes import Shape

if TYPE_CHECKING:
    from efficio.objects.gaskets import GasketDesign, GasketFace, GasketParameters

Color = Tuple[int, int, int]
"""8-bit RGB colour used for previews."""

DEFAULT_PREVIEW_COLOR: Color = (176, 182, 190)

T = TypeVar("T", bound="EfficioObject")


class EfficioObject:
    """Base class for every modelled object.

    Preview colour is inherited: an object without its own ``preview_color``
    takes its parent's resolved colour (e.g. the sub-assembly it belongs to),
    and an object with no parent takes the renderer's current colour.  So only
    major assemblies need a colour; individual parts may override it.
    """

    preview_color: Optional[Color] = None
    parent: Optional["EfficioObject"] = None

    def gasket_faces(self) -> dict[str, "GasketFace"]:
        """Explicit declarations; shape generation never silently inserts a gasket."""
        return {}

    def generate_gasket(
        self, name: str, parameters: "GasketParameters"
    ) -> "GasketDesign":
        faces = self.gasket_faces()
        if name not in faces:
            raise ValueError(f"Unknown gasket face {name!r}; available: {list(faces)}")
        return faces[name].generate(parameters)

    def cut(self) -> Optional[Shape]:
        return None

    def shape(self) -> Optional[Shape]:
        raise NotImplementedError("EfficioObject::shape()")

    def with_preview_color(self: T, color: Optional[Color]) -> T:
        self.preview_color = color
        return self

    def resolved_preview_color(self, current: Color = DEFAULT_PREVIEW_COLOR) -> Color:
        if self.preview_color is not None:
            return self.preview_color
        if self.parent is not None:
            return self.parent.resolved_preview_color(current)
        return current
