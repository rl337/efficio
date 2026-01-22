from typing import Optional

from efficio.objects.shapes import Shape


class EfficioObject:

    def cut(self) -> Optional[Shape]:
        return None

    def shape(self) -> Optional[Shape]:
        raise NotImplementedError("EfficioObject::shape()")
