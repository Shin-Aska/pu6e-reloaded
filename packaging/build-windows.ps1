$ErrorActionPreference = "Stop"

$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location $projectDirectory

if ($env:RELEASE_VERSION) {
    $releaseVersion = $env:RELEASE_VERSION.TrimStart("v")
} else {
    $releaseVersion = uv run --no-sync python -c "from importlib.metadata import version; print(version('pu6e-reloaded'))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not determine the application version."
    }
}

$releaseDirectory = Join-Path $projectDirectory "dist/release"
$portableParent = Join-Path $projectDirectory "dist/windows"
$portableDirectory = Join-Path $portableParent "pu6e-reloaded"
$buildDirectory = Join-Path $projectDirectory "build/pyinstaller/windows"
$iconPath = Join-Path $buildDirectory "pu6e-reloaded.ico"

New-Item -ItemType Directory -Force -Path $releaseDirectory, $buildDirectory | Out-Null

$iconRenderer = 'import sys; from PySide6.QtCore import QSize; from PySide6.QtGui import QGuiApplication, QImage, QPainter; from PySide6.QtSvg import QSvgRenderer; app = QGuiApplication([]); image = QImage(QSize(256, 256), QImage.Format.Format_ARGB32); image.fill(0); painter = QPainter(image); QSvgRenderer(sys.argv[1]).render(painter); painter.end(); sys.exit(0 if image.save(sys.argv[2]) else 1)'
uv run --no-sync python -c $iconRenderer (Join-Path $PSScriptRoot "pu6e-reloaded.svg") $iconPath
if ($LASTEXITCODE -ne 0) {
    throw "Could not render the Windows application icon."
}

$sharedArguments = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "pu6e-reloaded",
    "--icon", $iconPath,
    "--collect-submodules", "OpenGL.platform",
    "--copy-metadata", "PyOpenGL",
    "--add-data", ((Join-Path $projectDirectory "LICENSE") + ":."),
    "--add-data", ((Join-Path $projectDirectory "NOTICE.md") + ":."),
    "--add-data", ((Join-Path $projectDirectory "THIRD_PARTY_NOTICES.md") + ":."),
    "--specpath", $buildDirectory,
    "pu6e.py"
)

uv run --no-sync pyinstaller `
    --onedir `
    --workpath (Join-Path $buildDirectory "portable") `
    --distpath $portableParent `
    @sharedArguments
if ($LASTEXITCODE -ne 0) {
    throw "The Windows portable executable build failed."
}

Copy-Item LICENSE, NOTICE.md, THIRD_PARTY_NOTICES.md -Destination $portableDirectory
$portableArchive = Join-Path $releaseDirectory "pu6e-reloaded-$releaseVersion-windows-x86_64.zip"
Compress-Archive -Path $portableDirectory -DestinationPath $portableArchive -Force

uv run --no-sync pyinstaller `
    --onefile `
    --workpath (Join-Path $buildDirectory "standalone") `
    --distpath $releaseDirectory `
    @sharedArguments
if ($LASTEXITCODE -ne 0) {
    throw "The standalone Windows executable build failed."
}

$standaloneExecutable = Join-Path $releaseDirectory "pu6e-reloaded.exe"
$releaseExecutable = Join-Path $releaseDirectory "pu6e-reloaded-$releaseVersion-windows-x86_64.exe"
Move-Item -Path $standaloneExecutable -Destination $releaseExecutable -Force

Write-Host "Windows release artifacts are available in $releaseDirectory"
