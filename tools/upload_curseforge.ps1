#Requires -Version 5.1
# Upload the current version to an existing CurseForge project.
#
# Prerequisites: the project must already exist on CurseForge (creating a project is a
# website action and goes through moderation), and you need an author API token from
# https://authors.curseforge.com/#/account/api-tokens
#
# Usage:
#   .\tools\upload_curseforge.ps1 -ProjectId 1234567 -ApiToken "<token>"
param(
    [Parameter(Mandatory = $true)][int]$ProjectId,
    [string]$ApiToken = $env:CURSEFORGE_API_TOKEN,
    [string]$ChangelogFile = '',
    [ValidateSet('release', 'beta', 'alpha')][string]$ReleaseType = 'release',
    [string]$GameVersion = '1.20.1',
    [string]$ModLoaderVersion = '47.4.21'
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$curl = 'C:\Windows\System32\curl.exe'
if (-not (Test-Path $curl)) { throw "curl.exe not found at $curl" }
if (-not $ApiToken) { throw 'no API token: pass -ApiToken or set CURSEFORGE_API_TOKEN' }

$props = @{}
Get-Content -LiteralPath (Join-Path $project 'gradle.properties') -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*(mod_[a-z_]+)\s*=\s*(.+?)\s*$') { $props[$Matches[1]] = $Matches[2] }
}
$version = $props['mod_version']
$jar = Join-Path $project ("{0}-{1}.jar" -f $props['mod_archive_name'], $version)
if (-not (Test-Path -LiteralPath $jar)) { throw "release jar not found: $jar" }
$buildJar = Join-Path $project ("build\libs\{0}" -f (Split-Path $jar -Leaf))
if ((Get-FileHash -LiteralPath $jar).Hash -ne (Get-FileHash -LiteralPath $buildJar).Hash) { throw 'root jar and build/libs jar differ; rebuild first' }

if (-not $ChangelogFile) {
    $ChangelogFile = Join-Path $project "publish\curseforge\changelog-$version-en.md"
}
$changelog = if (Test-Path -LiteralPath $ChangelogFile) { Get-Content -LiteralPath $ChangelogFile -Raw -Encoding UTF8 } else { "Release $version" }

Write-Output "--- resolving game version ids ---"
$versionsJson = & $curl -s -H "X-Api-Token: $ApiToken" 'https://minecraft.curseforge.com/api/game/versions'
if ($LASTEXITCODE -ne 0) { throw "game/versions request failed (exit $LASTEXITCODE)" }
$versions = $versionsJson | ConvertFrom-Json
$mc = $versions | Where-Object { $_.name -eq $GameVersion } | Select-Object -First 1
$forge = $versions | Where-Object { $_.name -eq $ModLoaderVersion } | Select-Object -First 1
if (-not $mc) { throw "Minecraft version '$GameVersion' not found in the CurseForge version list" }
if (-not $forge) { throw "Forge version '$ModLoaderVersion' not found; pass -ModLoaderVersion with an exact CurseForge Forge version" }
Write-Output ("Minecraft {0} -> id {1}; Forge {2} -> id {3}" -f $mc.name, $mc.id, $forge.name, $forge.id)

$metadata = @{
    changelog     = $changelog
    changelogType = 'markdown'
    displayName   = "$version"
    releaseType   = $ReleaseType
    gameVersions  = @([int]$mc.id, [int]$forge.id)
} | ConvertTo-Json -Compress
$metadataPath = Join-Path $env:TEMP ("cf-metadata-{0}.json" -f $version)
[System.IO.File]::WriteAllText($metadataPath, $metadata, (New-Object System.Text.UTF8Encoding $false))

Write-Output "--- uploading $([System.IO.Path]::GetFileName($jar)) ---"
$response = & $curl -s -H "X-Api-Token: $ApiToken" -F "metadata=<$metadataPath;type=application/json" -F "file=@$jar" "https://minecraft.curseforge.com/api/projects/$ProjectId/upload"
Remove-Item -LiteralPath $metadataPath -Force -ErrorAction SilentlyContinue
Write-Output $response
if ($LASTEXITCODE -ne 0) { throw "upload failed (exit $LASTEXITCODE)" }
Write-Output 'CurseForge upload request finished.'
