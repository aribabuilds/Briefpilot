$ErrorActionPreference = "Stop"
$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")

function Copy-IfMissing($example, $target) {
    if (Test-Path $target) {
        Write-Host "skip: $target already exists"
    } else {
        Copy-Item $example $target
        Write-Host "created: $target"
    }
}

Copy-IfMissing (Join-Path $rootDir ".env.example") (Join-Path $rootDir ".env")
Copy-IfMissing (Join-Path $rootDir "frontend\.env.example") (Join-Path $rootDir "frontend\.env")
Copy-IfMissing (Join-Path $rootDir "backend\.env.example") (Join-Path $rootDir "backend\.env")
