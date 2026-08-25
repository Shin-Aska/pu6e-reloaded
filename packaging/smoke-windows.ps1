param(
    [Parameter(Mandatory = $true)]
    [string]$Executable
)

$ErrorActionPreference = "Stop"
$executablePath = (Resolve-Path $Executable).Path
$runtimeDirectory = Join-Path $env:RUNNER_TEMP "pu6e-smoke-$([guid]::NewGuid())"
New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null

$errorLog = Join-Path $runtimeDirectory "launcher-error.log"
$application = Start-Process `
    -FilePath $executablePath `
    -RedirectStandardError $errorLog `
    -PassThru

try {
    $deadline = [DateTime]::UtcNow.AddSeconds(90)

    do {
        $application.Refresh()
        if ($application.HasExited) {
            if (Test-Path $errorLog) {
                Get-Content $errorLog
            }
            throw "The packaged launcher exited before creating its window."
        }

        $candidates = @($application)
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($application.Id)"
        foreach ($child in $children) {
            $candidate = Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
            if ($candidate) {
                $candidates += $candidate
            }
        }

        foreach ($candidate in $candidates) {
            $candidate.Refresh()
            if ($candidate.MainWindowTitle -like "pu6e Reloaded*") {
                Write-Host "Verified packaged launcher window: $executablePath"
                return
            }
        }

        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)

    throw "Timed out waiting for the packaged launcher window."
} finally {
    if (-not $application.HasExited) {
        Stop-Process -Id $application.Id -Force -ErrorAction SilentlyContinue
    }
}
