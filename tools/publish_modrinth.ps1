#Requires -Version 5.1
# Publish the current build to Modrinth: create the project (draft), upload the version,
# then add the gallery images. All field values come from publish/modrinth/meta.json.
#
# Requires a Modrinth personal access token with the scopes
#   PROJECT_CREATE, PROJECT_WRITE, VERSION_CREATE
# created at https://modrinth.com/settings/pats . The API is reachable from a normal
# connection (no bot challenge), unlike the CurseForge author host.
#
# Usage:
#   .\tools\publish_modrinth.ps1 -Token "<mrp_...>"                 # create project + version + gallery
#   .\tools\publish_modrinth.ps1 -Token "<mrp_...>" -ProjectId ABCD # add version + gallery to an existing project
#   .\tools\publish_modrinth.ps1 -Token "<mrp_...>" -DryRun         # validate everything, send nothing
param(
    [string]$Token = $env:MODRINTH_TOKEN,
    [string]$ProjectId = '',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$curl = 'C:\Windows\System32\curl.exe'
$api = 'https://api.modrinth.com/v2'
if (-not (Test-Path $curl)) { throw "curl.exe not found at $curl" }
if (-not $Token) { throw 'no token: pass -Token or set MODRINTH_TOKEN' }

$meta = Get-Content -LiteralPath (Join-Path $project 'publish/modrinth/meta.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$p = $meta.project
$v = $meta.version

$bodyText = [System.IO.File]::ReadAllText((Join-Path $project $p.body_file), [System.Text.Encoding]::UTF8)
$changelog = [System.IO.File]::ReadAllText((Join-Path $project $v.changelog_file), [System.Text.Encoding]::UTF8)
$iconPath = Join-Path $project $p.icon_file
$jarPath = Join-Path $project $v.file
foreach ($f in @($iconPath, $jarPath)) { if (-not (Test-Path -LiteralPath $f)) { throw "missing file: $f" } }
$buildJar = Join-Path $project ("build/libs/" + (Split-Path $jarPath -Leaf))
if ((Get-FileHash -LiteralPath $jarPath).Hash -ne (Get-FileHash -LiteralPath $buildJar).Hash) { throw 'root jar and build/libs jar differ; rebuild first' }
Write-Output ("jar: {0}  sha256 {1}" -f (Split-Path $jarPath -Leaf), (Get-FileHash -LiteralPath $jarPath).Hash)

function Invoke-ModrinthJson {
    param([string]$Method, [string]$Uri, [string[]]$Form, [string]$Body = '')
    $args = @('-s', '-X', $Method, '-H', "Authorization: $Token", '-H', 'Accept: application/json')
    foreach ($f in $Form) { $args += @('-F', $f) }
    $out = & $curl @args $Uri
    return $out
}

if ($DryRun) {
    Write-Output '--- dry run ---'
    Write-Output ("project: {0} ({1})  type={2}  categories={3}" -f $p.title, $p.slug, $p.project_type, ($p.categories -join ', '))
    Write-Output ("license: {0}   sides: client={1} server={2}" -f $p.license_id, $p.client_side, $p.server_side)
    Write-Output ("version: {0} {1} {2} loaders={3} game={4}" -f $v.version_number, $v.version_type, $v.file, ($v.loaders -join ','), ($v.game_versions -join ','))
    Write-Output ("body chars: {0}   changelog chars: {1}   gallery items: {2}" -f $bodyText.Length, $changelog.Length, @($meta.gallery).Count)
    $existing = & $curl -s -o NUL -w '%{http_code}' -H 'Accept: application/json' "$api/project/$($p.slug)"
    Write-Output ("slug '$($p.slug)' already taken? HTTP $existing (404 = free)")
    return
}

$tmp = Join-Path $env:TEMP ('modrinth-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    if (-not $ProjectId) {
        $payload = [ordered]@{
            slug         = $p.slug
            title        = $p.title
            description  = $p.summary
            body         = $bodyText
            categories   = @($p.categories)
            project_type = $p.project_type
            license_id   = $p.license_id
            client_side  = $p.client_side
            server_side  = $p.server_side
            source_url   = $p.source_url
            issues_url   = $p.issues_url
            status       = 'draft'
        } | ConvertTo-Json -Depth 5
        $dataPath = Join-Path $tmp 'project.json'
        [System.IO.File]::WriteAllText($dataPath, $payload, (New-Object System.Text.UTF8Encoding $false))
        Write-Output '--- creating project (draft) ---'
        $resp = Invoke-ModrinthJson -Method POST -Uri "$api/project" -Form @("data=@$dataPath;type=application/json", "icon=@$iconPath;type=image/png")
        Write-Output $resp
        try { $ProjectId = ($resp | ConvertFrom-Json).id } catch { throw "could not parse project response: $resp" }
        if (-not $ProjectId) { throw "project creation failed: $resp" }
        Write-Output ("project id: $ProjectId")
        Start-Sleep -Seconds 3
    } else {
        Write-Output ("using existing project: $ProjectId")
    }

    $versionPayload = [ordered]@{
        name           = $v.name
        version_number = $v.version_number
        changelog      = $changelog
        dependencies   = @()
        game_versions  = @($v.game_versions)
        version_type   = $v.version_type
        loaders        = @($v.loaders)
        project_id     = $ProjectId
        file_parts     = @('file')
        primary_file   = 'file'
        status         = 'listed'
    } | ConvertTo-Json -Depth 5
    $versionPath = Join-Path $tmp 'version.json'
    [System.IO.File]::WriteAllText($versionPath, $versionPayload, (New-Object System.Text.UTF8Encoding $false))
    Write-Output '--- uploading version ---'
    $vresp = Invoke-ModrinthJson -Method POST -Uri "$api/version" -Form @("data=@$versionPath;type=application/json", "file=@$jarPath;type=application/java-archive")
    Write-Output $vresp
    $versionId = ''
    try { $versionId = ($vresp | ConvertFrom-Json).id } catch { }
    if (-not $versionId) { throw "version upload failed: $vresp" }
    Write-Output ("version id: $versionId")

    $ordering = 0
    foreach ($item in $meta.gallery) {
        $imgPath = Join-Path $project $item.file
        if (-not (Test-Path -LiteralPath $imgPath)) { Write-Output ("skip missing gallery file: " + $item.file); continue }
        $ext = [System.IO.Path]::GetExtension($imgPath).TrimStart('.').ToLower()
        $featured = if ($item.featured) { 'true' } else { 'false' }
        $title = [uri]::EscapeDataString([string]$item.title)
        $desc = [uri]::EscapeDataString([string]$item.description)
        $uri = "$api/project/$ProjectId/gallery?ext=$ext&featured=$featured&ordering=$ordering&title=$title&description=$desc"
        $code = & $curl -s -o NUL -w '%{http_code}' -X POST -H "Authorization: $Token" -H "Content-Type: image/$ext" --data-binary "@$imgPath" $uri
        Write-Output ("gallery [{0}] {1} -> HTTP {2}" -f $ordering, (Split-Path $imgPath -Leaf), $code)
        $ordering++
    }

    Write-Output ''
    Write-Output ("project page: https://modrinth.com/mod/{0}" -f $p.slug)
    Write-Output 'The project was created as a DRAFT. Review it on the website and hit'
    Write-Output '"Submit for review" when everything looks right.'
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
