# Measures end-to-end /analyze latency per analysis type, and compares it to
# the `estimated_seconds` each type advertises in the registry.
#
#   .\collect_latency.ps1 -Api "https://kairos-api-...run.app" -Runs 3
#
# Output: latency_raw.csv + latency_summary.csv
#
# Why the comparison matters: the registry promises the user a duration before
# they commit to a run. Whether those promises are true is a measurable claim,
# and "our own advertised estimates were optimistic by X%" is a finding worth
# reporting either way.

param(
    [Parameter(Mandatory=$true)][string]$Api,
    [int]$Runs = 3,
    [string]$OutDir = "."
)

$ErrorActionPreference = "Continue"

# One city-scale AOI per type, each over a window where data is known to exist.
# Keep these fixed across runs - latency is only comparable at constant AOI size.
$cases = @(
    @{ type="flood_extent";       bbox=@(89.3,25.0,89.9,25.5);        start="2017-08-10"; end="2017-08-31"; label="Brahmaputra, BD" },
    @{ type="wildfire_burn_scar"; bbox=@(-121.75,39.65,-121.35,39.95); start="2018-11-08"; end="2018-12-08"; label="Camp Fire, CA" },
    @{ type="deforestation";      bbox=@(-63.6,-9.8,-63.1,-9.4);      start="2020-06-01"; end="2020-09-30"; label="Rondonia, BR" },
    @{ type="ship_detection";     bbox=@(103.6,1.1,104.1,1.4);        start="2024-01-01"; end="2024-01-31"; label="Singapore Strait" },
    @{ type="oil_spill";          bbox=@(-89.5,28.6,-89.0,29.0);      start="2024-01-01"; end="2024-01-31"; label="Gulf of Mexico" },
    @{ type="urban_growth";       bbox=@(113.8,22.5,114.3,22.8);      start="2024-01-01"; end="2024-03-31"; label="Shenzhen" }
)

# Advertised durations from gee/registry.py, for the promised-vs-actual column.
$advertised = @{
    flood_extent = 20; wildfire_burn_scar = 20; deforestation = 30
    ship_detection = 30; oil_spill = 25; urban_growth = 25
}

Write-Host "Warming the service (first call absorbs any cold start)..." -ForegroundColor DarkGray
try { Invoke-RestMethod "$Api/health" -TimeoutSec 60 | Out-Null } catch {}

$rows = @()
foreach ($c in $cases) {
    for ($i = 1; $i -le $Runs; $i++) {
        Write-Host ("[{0}] run {1} of {2} ..." -f $c.type, $i, $Runs) -NoNewline
        $body = @{
            analysis_type = $c.type; bbox = $c.bbox
            start_date = $c.start; end_date = $c.end
        } | ConvertTo-Json -Compress

        $started = Get-Date
        try {
            $resp = Invoke-RestMethod -Method Post -Uri "$Api/analyze" `
                        -ContentType "application/json" -Body $body -TimeoutSec 300
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $rows += [pscustomobject]@{
                analysis_type = $c.type; aoi = $c.label; run = $i
                seconds = [math]::Round($elapsed, 2)
                confidence = $resp.confidence
                headline_value = $resp.headline_stat.value
                headline_unit = $resp.headline_stat.unit
                error = ""
            }
            Write-Host (" {0}s" -f [math]::Round($elapsed,1)) -ForegroundColor Green
        }
        catch {
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $rows += [pscustomobject]@{
                analysis_type = $c.type; aoi = $c.label; run = $i
                seconds = [math]::Round($elapsed, 2)
                confidence = $null; headline_value = $null; headline_unit = ""
                error = $_.Exception.Message
            }
            Write-Host " FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

$rawPath = Join-Path $OutDir "latency_raw.csv"
$rows | Export-Csv -Path $rawPath -NoTypeInformation -Encoding UTF8
Write-Host "`nWrote $rawPath" -ForegroundColor Cyan

$summary = $rows | Where-Object { $_.error -eq "" } | Group-Object analysis_type | ForEach-Object {
    $secs = ($_.Group | ForEach-Object { $_.seconds }) | Sort-Object
    $median = if ($secs.Count % 2 -eq 1) { $secs[[math]::Floor($secs.Count/2)] }
              else { [math]::Round((($secs[$secs.Count/2 - 1] + $secs[$secs.Count/2]) / 2), 2) }
    $adv = $advertised[$_.Name]
    [pscustomobject]@{
        analysis_type   = $_.Name
        runs            = $_.Group.Count
        median_seconds  = $median
        min_seconds     = $secs[0]
        max_seconds     = $secs[-1]
        advertised_secs = $adv
        vs_advertised   = if ($adv) { "{0:+0.0;-0.0}x" -f ($median / $adv) } else { "" }
    }
}

$sumPath = Join-Path $OutDir "latency_summary.csv"
$summary | Export-Csv -Path $sumPath -NoTypeInformation -Encoding UTF8
$summary | Format-Table -AutoSize
Write-Host "Wrote $sumPath" -ForegroundColor Cyan
Write-Host "`nReport median_seconds per type. If vs_advertised is far from 1.0," -ForegroundColor Yellow
Write-Host "that gap is itself a finding - say so rather than quietly fixing it." -ForegroundColor Yellow
