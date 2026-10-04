#Requires -Version 5.1
# Install the current version from the project into a Forge instance, keeping the old jar in a sibling backup.
# -RefreshBaseline re-records the hashes of the other mod files without installing (use after intentionally
# changing another mod); a normal install also refreshes the baseline so newly added mods get tracked.
param(
    [string]$InstancePath = "$env:APPDATA\.minecraft\versions\1.20.1-Forge_47.2.18-OptiFine_I6",
    [switch]$RefreshBaseline
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$props = @{}
Get-Content -LiteralPath (Join-Path $project 'gradle.properties') -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*(mod_[a-z_]+)\s*=\s*(.+?)\s*$') { $props[$Matches[1]] = $Matches[2] }
}
$version = $props['mod_version']
$archive = $props['mod_archive_name']
$name = "$archive-$version.jar"
$sourcePath = Join-Path $project $name
$buildPath = Join-Path $project "build\libs\$name"
$modsPath = Join-Path $InstancePath 'mods'
if (-not (Test-Path -LiteralPath $modsPath)) { throw "mods directory not found: $modsPath" }
$baselinePath = Join-Path $PSScriptRoot 'mods-baseline.json'

function Get-ModsSnapshot {
    param([string]$ModsPath, [string]$Archive)
    Get-ChildItem -LiteralPath $ModsPath -File |
        Where-Object { $_.Name -notlike "$Archive-*.jar" } |
        ForEach-Object { [pscustomobject]@{ Name = $_.Name; Length = $_.Length; SHA256 = (Get-FileHash -LiteralPath $_.FullName).Hash } }
}
function Save-ModsBaseline {
    param([string]$Path, $Snapshot)
    [System.IO.File]::WriteAllText($Path, ($Snapshot | ConvertTo-Json), (New-Object System.Text.UTF8Encoding $true))
}
function Assert-ModsBaseline {
    param([string]$Path, [string]$ModsPath)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $baseline = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($rec in $baseline) {
        $p = Join-Path $ModsPath $rec.Name
        if (-not (Test-Path -LiteralPath $p)) { throw "baseline file missing: $($rec.Name)" }
        if ((Get-FileHash -LiteralPath $p).Hash -ne $rec.SHA256) {
            throw "file differs from baseline: $($rec.Name)  (use -RefreshBaseline if this change is intentional)"
        }
    }
}

if ($RefreshBaseline) {
    $snapshot = @(Get-ModsSnapshot -ModsPath $modsPath -Archive $archive)
    Save-ModsBaseline -Path $baselinePath -Snapshot $snapshot
    Write-Output ("baseline refreshed: {0} file(s) recorded from {1}" -f $snapshot.Count, $modsPath)
    return
}

$newPath = Join-Path $modsPath $name
if (Test-Path -LiteralPath $newPath) { throw "already installed: $newPath (remove or back it up manually if this is an intentional rebuild)" }
$sourceHash = (Get-FileHash -LiteralPath $sourcePath).Hash
if ($sourceHash -ne (Get-FileHash -LiteralPath $buildPath).Hash) { throw 'root jar and build/libs jar differ; rebuild first' }

Assert-ModsBaseline -Path $baselinePath -ModsPath $modsPath

$installed = @(Get-ChildItem -LiteralPath $modsPath -File -Filter "$archive-*.jar")
if ($installed.Count -gt 1) { throw "multiple installed $archive jars found, clean up manually: $($installed.Name -join ', ')" }
$oldJar = $null
$backupPath = $null
if ($installed.Count -eq 1) {
    $oldJar = $installed[0]
    $oldVersion = $oldJar.BaseName.Substring($archive.Length + 1)
    $backupDir = Join-Path $InstancePath ("mods-backup-$oldVersion-" + (Get-Date -Format 'yyyy-MM-dd'))
    if (Test-Path -LiteralPath $backupDir) { throw "backup directory already exists: $backupDir" }
    $backupPath = Join-Path $backupDir $oldJar.Name
}
$stagePath = Join-Path $InstancePath "$archive-$version-install-staging.jar"
if (Test-Path -LiteralPath $stagePath) { throw "staging file already exists: $stagePath" }

Copy-Item -LiteralPath $sourcePath -Destination $stagePath
if ((Get-FileHash -LiteralPath $stagePath).Hash -ne $sourceHash) { throw 'staged jar hash mismatch' }
if ($oldJar) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Move-Item -LiteralPath $oldJar.FullName -Destination $backupPath
}
try {
    Move-Item -LiteralPath $stagePath -Destination $newPath
    if ((Get-FileHash -LiteralPath $newPath).Hash -ne $sourceHash) { throw 'installed jar hash mismatch' }
    Assert-ModsBaseline -Path $baselinePath -ModsPath $modsPath
} catch {
    if (Test-Path -LiteralPath $newPath) { Move-Item -LiteralPath $newPath -Destination $stagePath }
    if ($oldJar) { Move-Item -LiteralPath $backupPath -Destination $oldJar.FullName }
    throw
}
$snapshot = @(Get-ModsSnapshot -ModsPath $modsPath -Archive $archive)
Save-ModsBaseline -Path $baselinePath -Snapshot $snapshot
[pscustomobject]@{
    Installed   = $newPath
    Version     = $version
    Bytes       = (Get-Item -LiteralPath $newPath).Length
    SHA256      = $sourceHash
    Replaced    = if ($oldJar) { $oldJar.Name } else { 'none (fresh install)' }
    Backup      = if ($backupPath) { $backupPath } else { 'none' }
    OtherFiles  = ("hashes unchanged; baseline refreshed with {0} tracked file(s)" -f $snapshot.Count)
} | ConvertTo-Json
