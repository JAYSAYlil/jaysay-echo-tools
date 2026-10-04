#Requires -Version 5.1
# Copy an existing isolated smoke world to a new name (quickPlay needs an existing save).
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Template = ''
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$saves = Join-Path $project 'run\saves'
if (-not (Test-Path $saves)) { throw "saves directory not found: $saves" }
$saves = (Resolve-Path -LiteralPath $saves).Path
$target = [System.IO.Path]::GetFullPath((Join-Path $saves $Name))
if (-not $target.StartsWith($saves + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'smoke world must be inside project run/saves' }
if (Test-Path $target) { throw "world already exists: $target" }
if (-not $Template) {
    $Template = Get-ChildItem -LiteralPath $saves -Directory |
        Where-Object { $_.Name -like 'echo-*-emissive' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty Name
}
if (-not $Template) { throw 'no template world found; pass -Template explicitly' }
$source = [System.IO.Path]::GetFullPath((Join-Path $saves $Template))
if (-not $source.StartsWith($saves + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'template must be inside project run/saves' }
if (-not (Test-Path $source)) { throw "template world not found: $source" }
Copy-Item -LiteralPath $source -Destination $target -Recurse
Remove-Item -LiteralPath (Join-Path $target 'session.lock') -ErrorAction SilentlyContinue
# older copies sometimes nested a whole world folder inside the save; drop that junk
Get-ChildItem -LiteralPath $target -Directory |
    Where-Object { $_.Name -like 'echo-*' -and (Test-Path (Join-Path $_.FullName 'level.dat')) } |
    ForEach-Object {
        $nestedWorld = [System.IO.Path]::GetFullPath($_.FullName)
        if (-not $nestedWorld.StartsWith($target + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'nested cleanup escaped copied smoke world' }
        Remove-Item -LiteralPath $nestedWorld -Recurse -Force
    }
Write-Output ("prepared smoke world '{0}' from template '{1}'" -f $Name, $Template)
