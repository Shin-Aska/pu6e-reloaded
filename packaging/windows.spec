import os
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

project_directory = Path(sys.argv[0]).resolve().parent.parent
onefile = "--onefile" in sys.argv[1:]

# Resolve Windows DLLs before unrelated tools on PATH, especially Qt's system ICU.
os.environ["PATH"] = os.pathsep.join([
    str(Path(os.environ["SystemRoot"]) / "System32"),
    os.environ["PATH"],
])

a = Analysis(
    [str(project_directory / "pu6e.py")],
    pathex=[str(project_directory)],
    datas=[
        (str(project_directory / name), ".")
        for name in ("LICENSE", "NOTICE.md", "THIRD_PARTY_NOTICES.md")
    ] + copy_metadata("PyOpenGL"),
    hiddenimports=collect_submodules("OpenGL.platform") + ["pu6e_qt.windows_opengl"],
)

# Analysis reclassifies DLL inputs as binaries and searches their dependencies.
# Add Mesa afterward so its OpenGL DLL stays isolated from Qt's native OpenGL.
a.datas += Tree(str(project_directory / "build/mesa/runtime"), prefix="mesa", typecode="DATA")

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries if onefile else [],
    a.datas if onefile else [],
    [],
    exclude_binaries=not onefile,
    name="pu6e-reloaded",
    console=False,
    upx=True,
    icon=str(project_directory / "build/pyinstaller/windows/pu6e-reloaded.ico"),
)

if not onefile:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        name="pu6e-reloaded",
        upx=True,
    )
