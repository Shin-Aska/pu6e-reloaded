[CmdletBinding()]
param([switch]$Help)

$ErrorActionPreference = "Stop"
if ($Help) {
    Write-Host "Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1"
    Write-Host "Sets up Python 3.14, locked development/build dependencies, and Windows Vulkan."
    return
}
if ($env:OS -ne "Windows_NT" -or $env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    throw "Use 64-bit Windows PowerShell on x86-64 Windows, or bash setup.sh on Linux/macOS."
}

$projectDirectory = $PSScriptRoot
$toolsDirectory = Join-Path $projectDirectory "build/tools"
$uvExecutable = Join-Path $toolsDirectory "uv.exe"
if (-not (Test-Path -LiteralPath $uvExecutable -PathType Leaf)) {
    $installedUv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($installedUv) {
        $uvExecutable = $installedUv.Source
    } else {
        New-Item -ItemType Directory -Force -Path $toolsDirectory | Out-Null
        $installer = Join-Path $toolsDirectory "uv-install.ps1"
        $previousInstallDirectory = $env:UV_UNMANAGED_INSTALL
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "https://astral.sh/uv/0.12.9/install.ps1" -OutFile $installer
            $env:UV_UNMANAGED_INSTALL = $toolsDirectory
            & $installer
            if (-not (Test-Path -LiteralPath $uvExecutable -PathType Leaf)) {
                throw "uv installation did not produce $uvExecutable."
            }
        } finally {
            $env:UV_UNMANAGED_INSTALL = $previousInstallDirectory
            if (Test-Path -LiteralPath $installer) {
                Remove-Item -LiteralPath $installer
            }
        }
    }
}

Push-Location $projectDirectory
try {
    & $uvExecutable sync --locked --python 3.14 --group packaging
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the locked Python environment." }
    & $uvExecutable pip check
    if ($LASTEXITCODE -ne 0) { throw "The Python environment has incompatible dependencies." }
    & (Join-Path $projectDirectory "packaging/prepare-windows-mesa.ps1") | Out-Null
    & (Join-Path $projectDirectory ".venv/Scripts/python.exe") -c "import numpy; import PySide6.QtWidgets; import OpenGL.GL"
    if ($LASTEXITCODE -ne 0) { throw "The installed application dependencies could not load." }
} finally {
    Pop-Location
}

Write-Host "Setup complete. Start the editor with: .\.venv\Scripts\python.exe .\pu6e.py"
Write-Host "In VS Code, use F5 to debug or Ctrl+Shift+B to compile."
