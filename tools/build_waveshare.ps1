[CmdletBinding()]
param(
    [ValidateSet('espnow')]
    [string]$Mode = 'espnow',

    [switch]$Clean,

    [switch]$SkipInstallerSync,

    [string]$Distribution = 'Debian'
)

$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$root = [System.IO.Path]::GetPathRoot($repository)
if ($root -notmatch '^([A-Za-z]):\\$') {
    throw "The repository must be on a Windows drive mounted by WSL: $repository"
}
$drive = $Matches[1].ToLowerInvariant()
$relativePath = $repository.Substring($root.Length).Replace('\', '/')
$repositoryWsl = "/mnt/$drive/$relativePath"

wsl -d $Distribution -- which docker *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker is not available in WSL distribution '$Distribution'. Enable Docker Desktop integration for it."
}

wsl -d $Distribution -- which rsync *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing rsync in $Distribution..."
    wsl -d $Distribution -u root -- apt-get update
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    wsl -d $Distribution -u root -- apt-get install -y rsync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$arguments = @(
    '-d', $Distribution,
    '--', 'bash', "$repositoryWsl/tools/build_waveshare_debian.sh",
    '--source', $repositoryWsl,
    '--mode', $Mode
)
if ($Clean) {
    $arguments += '--clean'
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
wsl @arguments
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($exitCode -eq 0 -and -not $SkipInstallerSync) {
    $installerRepository = Join-Path (Split-Path -Parent $repository) 'esp32-p4-micropython-installer'
    $installerUpdater = Join-Path $installerRepository 'update_firmware.py'
    $python = Join-Path $repository '.venv\Scripts\python.exe'

    if ((Test-Path $installerUpdater) -and (Test-Path $python)) {
        Write-Host "Synchronizing firmware with: $installerRepository"
        & $python $installerUpdater --sync-lvgl $repository
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } else {
        Write-Host 'Installer sibling not found; skipping firmware synchronization.'
    }
}

exit $exitCode
