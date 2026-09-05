$ErrorActionPreference = "Stop"

$projectDirectory = Split-Path -Parent $PSScriptRoot
$cacheDirectory = Join-Path $projectDirectory "build/mesa"
$runtimeDirectory = Join-Path $cacheDirectory "runtime"
$mesaVersion = "26.2.2"
$llvmVersion = "23.1.0"
$vulkanVersion = "1.4.357.0"
$releaseUrl = "https://github.com/mmozeiko/build-mesa/releases/download/$mesaVersion"
$tarExecutable = Join-Path $env:WINDIR "System32/tar.exe"

if (-not (Test-Path -LiteralPath $tarExecutable -PathType Leaf)) {
    throw "Windows tar.exe is required to prepare the bundled Mesa drivers."
}

New-Item -ItemType Directory -Force -Path $cacheDirectory | Out-Null

function Get-VerifiedDownload {
    param(
        [string]$Url,
        [string]$FileName,
        [string]$Sha256
    )

    $destination = Join-Path $cacheDirectory $FileName
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $Sha256) {
            throw "Checksum mismatch for $destination. Remove the cached file and run the build again."
        }
        return $destination
    }

    Write-Host "Downloading $FileName"
    $downloadPath = "$destination.download"
    Invoke-WebRequest -Uri $Url -OutFile $downloadPath -UseBasicParsing
    if ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash -ne $Sha256) {
        throw "Checksum mismatch for $FileName. The Mesa runtime was not prepared."
    }
    Move-Item -LiteralPath $downloadPath -Destination $destination -Force
    return $destination
}

$zinkArchive = Get-VerifiedDownload `
    -Url "$releaseUrl/mesa-zink-x64-$mesaVersion.7z" `
    -FileName "mesa-zink-x64-$mesaVersion.7z" `
    -Sha256 "bcab5c75818f831cdc0053841c10fb4e5e0ba08598b3defe6127e26e34c75f22"
$lavapipeArchive = Get-VerifiedDownload `
    -Url "$releaseUrl/mesa-lavapipe-x64-$mesaVersion.7z" `
    -FileName "mesa-lavapipe-x64-$mesaVersion.7z" `
    -Sha256 "b5b06e340621aa8607d0f53c61949dce49c38245d746fe284870060109f65929"
$mesaSource = Get-VerifiedDownload `
    -Url "https://archive.mesa3d.org/mesa-$mesaVersion.tar.xz" `
    -FileName "mesa-$mesaVersion.tar.xz" `
    -Sha256 "eeb29ca7e56cfaa8e8a79538dcf834e3b18e501c31bef5145e959ea437cc4216"
$llvmLicense = Get-VerifiedDownload `
    -Url "https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-$llvmVersion/llvm/LICENSE.TXT" `
    -FileName "llvm-$llvmVersion-LICENSE.TXT" `
    -Sha256 "8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee"
$vulkanArchiveName = "VulkanRT-X64-$vulkanVersion-Components"
$vulkanArchive = Get-VerifiedDownload `
    -Url "https://sdk.lunarg.com/sdk/download/$vulkanVersion/windows/$vulkanArchiveName.zip" `
    -FileName "$vulkanArchiveName.zip" `
    -Sha256 "a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83"

$zinkDirectory = Join-Path $runtimeDirectory "zink"
$lavapipeDirectory = Join-Path $runtimeDirectory "lavapipe"
$mesaLicenseDirectory = Join-Path $runtimeDirectory "licenses/mesa-$mesaVersion"
$llvmLicenseDirectory = Join-Path $runtimeDirectory "licenses/llvm-$llvmVersion"
$vulkanLicenseDirectory = Join-Path $runtimeDirectory "licenses/vulkan-$vulkanVersion"
New-Item -ItemType Directory -Force -Path `
    $zinkDirectory, $lavapipeDirectory, $mesaLicenseDirectory, $llvmLicenseDirectory, $vulkanLicenseDirectory | Out-Null

& $tarExecutable -xf $zinkArchive -C $zinkDirectory opengl32.dll
if ($LASTEXITCODE -ne 0) {
    throw "Could not extract the bundled Mesa Zink driver."
}
& $tarExecutable -xf $lavapipeArchive -C $lavapipeDirectory vulkan_lvp.dll lvp_icd.x86_64.json
if ($LASTEXITCODE -ne 0) {
    throw "Could not extract the bundled Mesa Lavapipe driver."
}
& $tarExecutable -xf $mesaSource -C $mesaLicenseDirectory --strip-components 1 `
    "mesa-$mesaVersion/docs/license.rst" "mesa-$mesaVersion/licenses"
if ($LASTEXITCODE -ne 0) {
    throw "Could not extract the Mesa license notices."
}
Copy-Item -LiteralPath $llvmLicense -Destination (Join-Path $llvmLicenseDirectory "LICENSE.TXT") -Force
& $tarExecutable -xf $vulkanArchive -C $runtimeDirectory --strip-components 2 `
    "$vulkanArchiveName/x64/vulkan-1.dll"
if ($LASTEXITCODE -ne 0) {
    throw "Could not extract the bundled Vulkan loader."
}
& $tarExecutable -xf $vulkanArchive -C $vulkanLicenseDirectory --strip-components 1 `
    "$vulkanArchiveName/VulkanRT-License.txt"
if ($LASTEXITCODE -ne 0) {
    throw "Could not extract the Vulkan runtime license notices."
}
Copy-Item -LiteralPath (Join-Path $mesaLicenseDirectory "licenses/Apache-2.0") `
    -Destination (Join-Path $vulkanLicenseDirectory "Apache-2.0") -Force

$requiredFiles = @(
    (Join-Path $zinkDirectory "opengl32.dll"),
    (Join-Path $lavapipeDirectory "vulkan_lvp.dll"),
    (Join-Path $lavapipeDirectory "lvp_icd.x86_64.json"),
    (Join-Path $mesaLicenseDirectory "docs/license.rst"),
    (Join-Path $mesaLicenseDirectory "licenses/MIT"),
    (Join-Path $llvmLicenseDirectory "LICENSE.TXT"),
    (Join-Path $runtimeDirectory "vulkan-1.dll"),
    (Join-Path $vulkanLicenseDirectory "VulkanRT-License.txt"),
    (Join-Path $vulkanLicenseDirectory "Apache-2.0")
)
foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf) -or (Get-Item -LiteralPath $requiredFile).Length -eq 0) {
        throw "The bundled Mesa runtime is incomplete: $requiredFile"
    }
}

Write-Host "Prepared Mesa $mesaVersion for Windows x86_64 in $runtimeDirectory"
return $runtimeDirectory
