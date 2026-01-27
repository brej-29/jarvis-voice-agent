Param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$mobileDir = Join-Path $root "..\mobile"

Set-Location $mobileDir

Write-Host "[mobile] Running flutter pub get"
flutter pub get

Write-Host "[mobile] Starting flutter run"
flutter run