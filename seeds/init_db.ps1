# Initialize Phase 1 database: create DB, schema, seed
# Usage: pwsh ./seeds/init_db.ps1

$ErrorActionPreference = "Stop"
$PgBin = "D:\soft\PostgreSQL\bin"
$Env:PGPASSWORD = if ($Env:PGPASSWORD) { $Env:PGPASSWORD } else { "123456" }
$PgUser = if ($Env:PGUSER) { $Env:PGUSER } else { "postgres" }
$PgHost = if ($Env:PGHOST) { $Env:PGHOST } else { "localhost" }
$DbName = if ($Env:PGDATABASE) { $Env:PGDATABASE } else { "fault_agent" }

$Psql = Join-Path $PgBin "psql.exe"
$SeedDir = $PSScriptRoot

Write-Host "==> Ensuring database '$DbName' exists..."
$exists = & $Psql -U $PgUser -h $PgHost -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName'"
if ($exists -ne "1") {
    & $Psql -U $PgUser -h $PgHost -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DbName;"
} else {
    Write-Host "    database already exists"
}

Write-Host "==> Applying schema..."
& $Psql -U $PgUser -h $PgHost -d $DbName -v ON_ERROR_STOP=1 -f (Join-Path $SeedDir "02_schema.sql")

Write-Host "==> Loading seed data..."
& $Psql -U $PgUser -h $PgHost -d $DbName -v ON_ERROR_STOP=1 -f (Join-Path $SeedDir "seed_demo.sql")

if (Test-Path (Join-Path $SeedDir "03_patch_wo_analysis_unique.sql")) {
    Write-Host "==> Applying incremental patches..."
    & $Psql -U $PgUser -h $PgHost -d $DbName -v ON_ERROR_STOP=1 -f (Join-Path $SeedDir "03_patch_wo_analysis_unique.sql")
}

if (Test-Path (Join-Path $SeedDir "04_app_user.sql")) {
    Write-Host "==> Applying app_user table + seed accounts..."
    & $Psql -U $PgUser -h $PgHost -d $DbName -v ON_ERROR_STOP=1 -f (Join-Path $SeedDir "04_app_user.sql")
}

Write-Host "==> Done. Connection tip:"
Write-Host "    postgresql+psycopg://postgres:***@localhost:5432/$DbName"
