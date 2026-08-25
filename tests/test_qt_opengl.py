from __future__ import annotations

import pytest
from PySide6.QtGui import QSurfaceFormat


class FakeOpenGLContext:
    def __init__(self, *, embedded: bool, core_profile: bool) -> None:
        self.embedded = embedded
        self.surface_format = QSurfaceFormat()
        if core_profile:
            self.surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

    def isOpenGLES(self) -> bool:
        return self.embedded

    def format(self) -> QSurfaceFormat:
        return self.surface_format


@pytest.mark.parametrize(
    ("embedded", "core_profile", "reason"),
    ((True, False, "OpenGL ES"), (False, True, "core-profile")),
)
def test_rejects_opengl_contexts_without_fixed_function_support(
    embedded: bool, core_profile: bool, reason: str
) -> None:
    from pu6e_qt.canvas import OpenGLCompatibilityError, validate_opengl_context

    with pytest.raises(OpenGLCompatibilityError, match=reason):
        validate_opengl_context(FakeOpenGLContext(embedded=embedded, core_profile=core_profile))


def test_rejects_a_missing_opengl_context() -> None:
    from pu6e_qt.canvas import OpenGLCompatibilityError, validate_opengl_context

    with pytest.raises(OpenGLCompatibilityError, match="did not create"):
        validate_opengl_context(None)
