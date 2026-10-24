$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Kotlinc = Get-Command 'kotlinc' -ErrorAction SilentlyContinue
if (-not $Kotlinc) {
    throw "Kotlin compiler 'kotlinc' was not found. Install Kotlin or run the Android Gradle unit tests instead."
}
$Temp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Temp | Out-Null
try {
    $Physics = Join-Path $Root 'engine/physics/src/main/java/com/verdant/os/engine/physics/Pendulum.kt'
    $Harness = Join-Path $Root 'scripts/PhysicsHarness.kt'
    $Jar = Join-Path $Temp 'verdant-physics-harness.jar'
    & $Kotlinc.Source $Physics $Harness '-include-runtime' '-d' $Jar
    if ($LASTEXITCODE -ne 0) { throw "kotlinc exited with code $LASTEXITCODE" }
    & java -jar $Jar
    if ($LASTEXITCODE -ne 0) { throw "physics harness exited with code $LASTEXITCODE" }
} finally {
    Remove-Item -Recurse -Force $Temp -ErrorAction SilentlyContinue
}
