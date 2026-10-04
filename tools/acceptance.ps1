#Requires -Version 5.1
# One-command acceptance: build -> package audit -> optional smoke -> optional install.
param(
    [switch]$Smoke,
    [switch]$Install,
    [string]$World = '',
    [string]$InstancePath = "$env:APPDATA\.minecraft\versions\1.20.1-Forge_47.2.18-OptiFine_I6"
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $project

$runtimeJdk = Join-Path $env:APPDATA '.minecraft\runtime\java-runtime-gamma-snapshot'
if (Test-Path -LiteralPath (Join-Path $runtimeJdk 'bin\java.exe')) {
    $env:JAVA_HOME = $runtimeJdk
} elseif (-not $env:JAVA_HOME) {
    throw 'no Java 17 runtime found: expected the Minecraft java-runtime-gamma-snapshot or JAVA_HOME'
}
if (-not $env:JAVA_TOOL_OPTIONS) {
    $trustStore = 'C:\Program Files\Eclipse Adoptium\jdk-26.0.2.10-hotspot\lib\security\cacerts'
    if (Test-Path -LiteralPath $trustStore) {
        $env:JAVA_TOOL_OPTIONS = '-Djavax.net.ssl.trustStore="' + $trustStore + '" -Djavax.net.ssl.trustStorePassword=changeit'
    }
}
$codexPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$python = if (Test-Path -LiteralPath $codexPython) { $codexPython } else { (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $python) {
    $bundled = Join-Path $env:USERPROFILE '.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { $python = $bundled }
}
if (-not $python) { throw 'python not found; tools/audit_package.py needs it' }

$props = @{}
Get-Content -LiteralPath (Join-Path $project 'gradle.properties') -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*(mod_[a-z_]+)\s*=\s*(.+?)\s*$') { $props[$Matches[1]] = $Matches[2] }
}
$version = $props['mod_version']
$archive = $props['mod_archive_name']
$modid = $props['mod_id']
$name = "$archive-$version.jar"
Write-Output "=== acceptance: $modid $version ==="

Write-Output '--- build ---'
cmd /c "gradlew.bat clean build --console=plain > build.log 2>&1"
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath (Join-Path $project 'build.log') -Tail 20 | Out-String | Write-Output; throw 'build failed (see build.log)' }
Copy-Item -LiteralPath (Join-Path $project "build\libs\$name") -Destination (Join-Path $project $name) -Force
Get-Content -LiteralPath (Join-Path $project 'build.log') -Tail 3 | Out-String | Write-Output
Write-Output "built $name"

Write-Output '--- package audit ---'
& $python (Join-Path $PSScriptRoot 'audit_package.py')
if ($LASTEXITCODE -ne 0) { throw 'package audit failed' }

if ($Smoke) {
    Write-Output '--- isolated client smoke ---'
    if (-not $World) { $World = 'echo-v' + ($version -replace '\.', '') + '-emissive' }
    $worldPath = Join-Path $project "run\saves\$World"
    if (-not (Test-Path -LiteralPath $worldPath)) {
        & (Join-Path $PSScriptRoot 'prepare-smoke-world.ps1') -Name $World
    } else {
        Write-Output "reusing existing smoke world '$World'"
    }
    $logDir = Join-Path $project "artwork\validation\v$version"
    if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
    $smokeLog = Join-Path $logDir 'emissive-smoke-final.log'
    $smokeStarted = Get-Date
    cmd /c "gradlew.bat runClient -PemissiveSmoke=true -PquickPlayWorld=$World --console=plain > artwork\validation\v$version\emissive-smoke-final.log 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "smoke client exited with an error (see $smokeLog)" }
    if (Select-String -LiteralPath $smokeLog -Pattern 'VERIFY FAIL' -Quiet) {
        Select-String -LiteralPath $smokeLog -Pattern 'VERIFY FAIL' | Select-Object -First 3 | ForEach-Object { $_.Line } | Write-Output
        throw "in-game /echo verify reported FAIL (see $smokeLog)"
    }
    if (-not (Select-String -LiteralPath $smokeLog -Pattern '\[Echo Pickaxe\] VERIFY PASS' -Quiet)) {
        throw "no '[Echo Pickaxe] VERIFY PASS' line in $smokeLog"
    }
    if (-not (Select-String -LiteralPath $smokeLog -Pattern '\[EchoEmissiveSmoke\] PASS:' -Quiet)) {
        throw "smoke did not report PASS (see $smokeLog)"
    }
    $shots = @(Get-ChildItem -LiteralPath (Join-Path $project 'run\screenshots') -Filter 'echo-emissive-*.png' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $smokeStarted })
    if ($shots.Count) { $shots | Copy-Item -Destination $logDir -Force }
    Write-Output ("smoke PASS (log: $smokeLog; archived {0} screenshot(s))" -f $shots.Count)
}

if ($Install) {
    Write-Output '--- install ---'
    & (Join-Path $PSScriptRoot 'install_release.ps1') -InstancePath $InstancePath
}
Write-Output '=== acceptance complete ==='
