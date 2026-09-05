param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [switch]$Hardware
)

$ErrorActionPreference = "Stop"
$reportPath = Join-Path ([System.IO.Path]::GetTempPath()) "pu6e-vulkan-$([guid]::NewGuid()).json"
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = (Resolve-Path -LiteralPath $Executable).Path
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardError = $true
$startInfo.CreateNoWindow = $true
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$startInfo.ArgumentList.Add("--renderer-probe")
$startInfo.ArgumentList.Add($reportPath)
foreach ($name in @("QT_QPA_PLATFORM", "QT_OPENGL_DLL", "PYOPENGL_PLATFORM", "VK_DRIVER_FILES", "VK_ICD_FILENAMES", "MESA_VK_DEVICE_SELECT", "VK_LOADER_DRIVERS_SELECT")) {
    $null = $startInfo.Environment.Remove($name)
}
if ($Hardware) {
    $null = $startInfo.Environment.Remove("LIBGL_ALWAYS_SOFTWARE")
} else {
    $startInfo.Environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
}
$startInfo.Environment["QT_LOGGING_RULES"] = "qt.qpa.gl=true"
$startInfo.Environment["VK_LOADER_DEBUG"] = "error,warn"
$probe = [System.Diagnostics.Process]::Start($startInfo)
$errorOutput = $probe.StandardError.ReadToEndAsync()
try {
    if (-not $probe.WaitForExit(60000)) {
        $probe.Kill($true)
        throw "The packaged Vulkan rendering check timed out."
    }
    $diagnostics = $errorOutput.GetAwaiter().GetResult()
    if ($diagnostics) {
        Write-Host $diagnostics.Trim()
    }
    if (Test-Path -LiteralPath $reportPath) {
        Write-Host "Vulkan probe report: $(Get-Content -LiteralPath $reportPath -Raw)"
    }
    if ($probe.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $reportPath)) {
        throw "The packaged Vulkan rendering check failed (exit $($probe.ExitCode))."
    }
    $result = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    if ($result.renderer -notmatch "zink" -or $result.pixel -ne "ff0000ff") {
        throw "The packaged Vulkan check did not render the expected triangle."
    }
    if (($result.renderer -match "llvmpipe") -eq [bool]$Hardware) {
        throw "The Vulkan check used the wrong device type: $($result.renderer)"
    }
    Write-Host "Verified Vulkan rendering: $($result.renderer); pixel=$($result.pixel)"
} finally {
    $probe.Dispose()
    if (Test-Path -LiteralPath $reportPath) {
        Remove-Item -LiteralPath $reportPath
    }
}
