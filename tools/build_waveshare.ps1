[CmdletBinding()]
param(
    [ValidateSet('espnow')]
    [string]$Mode = 'espnow',

    [switch]$Clean,

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
exit $exitCode
