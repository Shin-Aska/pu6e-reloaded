param(
    [Parameter(Mandatory = $true)]
    [string]$RuntimeDirectory
)

$ErrorActionPreference = "Stop"
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if ($principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Windows package smoke checks must run without administrator privileges."
}

# PsExec's limited token needs writable temporary storage for onefile extraction.
$env:TEMP = $RuntimeDirectory
$env:TMP = $RuntimeDirectory
$env:RUNNER_TEMP = $RuntimeDirectory
Write-Host "Verifying Windows packages without administrator privileges."

$portable = "./dist/windows/pu6e-reloaded/pu6e-reloaded.exe"
$standalone = (Get-ChildItem ./dist/release/*-windows-x86_64.exe).FullName
foreach ($executable in @($portable, $standalone)) {
    & "$PSScriptRoot/smoke-windows-vulkan.ps1" -Executable $executable
    & "$PSScriptRoot/smoke-windows.ps1" -Executable $executable
}
