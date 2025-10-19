from typing import Optional

from efficio.objects.shapes import EfficioShape


class EfficioObject:

    def cut(self) -> Optional[EfficioShape]:
        return None

    def shape(self) -> Optional[EfficioShape]:
        raise NotImplementedError("EfficioObject::shape()")
