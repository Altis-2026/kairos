# Runs every ground-truth benchmark N times and writes one row per run.
#
#   .\collect_benchmarks.ps1 -Api "https://kairos-api-77017849721.us-central1.run.app" -Runs 5
#
# Output: benchmarks_raw.csv (one row per run) + benchmarks_summary.csv
#         (mean/min/max per benchmark — this is what goes in the paper table).
#
# Each run is a full production analysis plus a reference comparison, so budget
# 30-90 s per run. 3 benchmarks x 5 runs is roughly 15-20 minutes; leave it going.

param(
    [Parameter(Mandatory=$true)][string]$Api,
    [int]$Runs = 5,
    [string]$OutDir = "."
)

$ErrorActionPreference = "Continue"
$benchmarks = @("bangladesh-monsoon-2017", "camp-fire-2018", "rondonia-clearing-2020")
$rows = @()

foreach ($bm in $benchmarks) {
    for ($i = 1; $i -le $Runs; $i++) {
        Write-Host "[$bm] run $i of $Runs ..." -NoNewline
        $started = Get-Date
        try {
            $body = @{ benchmark_id = $bm } | ConvertTo-Json -Compress
            $resp = Invoke-RestMethod -Method Post -Uri "$Api/validation/run" `
                        -ContentType "application/json" -Body $body -TimeoutSec 300
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $m = $resp.metrics

            $rows += [pscustomobject]@{
                benchmark          = $bm
                run                = $i
                analysis_type      = $resp.benchmark.analysis_type
                iou                = $m.iou
                precision          = $m.precision
                recall             = $m.recall
                f1                 = $m.f1
                kairos_area_km2    = $m.kairos_area_km2
                reference_area_km2 = $m.reference_area_km2
                intersection_km2   = $m.intersection_km2
                union_km2          = $m.union_km2
                data_date          = $resp.data_date
                seconds            = [math]::Round($elapsed, 1)
                error              = ""
            }
            Write-Host (" IoU={0} P={1} R={2} F1={3}  ({4}s)" -f `
                $m.iou, $m.precision, $m.recall, $m.f1, [math]::Round($elapsed,1)) `
                -ForegroundColor Green
        }
        catch {
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $rows += [pscustomobject]@{
                benchmark = $bm; run = $i; analysis_type = ""
                iou = $null; precision = $null; recall = $null; f1 = $null
                kairos_area_km2 = $null; reference_area_km2 = $null
                intersection_km2 = $null; union_km2 = $null; data_date = ""
                seconds = [math]::Round($elapsed, 1)
                error = $_.Exception.Message
            }
            Write-Host " FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

$rawPath = Join-Path $OutDir "benchmarks_raw.csv"
$rows | Export-Csv -Path $rawPath -NoTypeInformation -Encoding UTF8
Write-Host "`nWrote $rawPath" -ForegroundColor Cyan

# Summary: mean/min/max per benchmark, over successful runs only.
$summary = $rows | Where-Object { $_.error -eq "" } | Group-Object benchmark | ForEach-Object {
    $g = $_.Group
    $mean = { param($f) [math]::Round((($g | Measure-Object -Property $f -Average).Average), 3) }
    [pscustomobject]@{
        benchmark       = $_.Name
        successful_runs = $g.Count
        mean_iou        = & $mean "iou"
        mean_precision  = & $mean "precision"
        mean_recall     = & $mean "recall"
        mean_f1         = & $mean "f1"
        iou_min         = ($g | Measure-Object -Property iou -Minimum).Minimum
        iou_max         = ($g | Measure-Object -Property iou -Maximum).Maximum
        mean_seconds    = & $mean "seconds"
    }
}

$sumPath = Join-Path $OutDir "benchmarks_summary.csv"
$summary | Export-Csv -Path $sumPath -NoTypeInformation -Encoding UTF8
$summary | Format-Table -AutoSize
Write-Host "Wrote $sumPath" -ForegroundColor Cyan
Write-Host "`nThe mean_iou / mean_precision / mean_recall / mean_f1 columns are the" -ForegroundColor Yellow
Write-Host "paper's accuracy table. iou_min..iou_max is your run-to-run stability." -ForegroundColor Yellow
