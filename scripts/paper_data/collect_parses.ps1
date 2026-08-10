# Runs every query in queries.jsonl through the NL parser (parse_only, so no
# analysis is executed) and writes a CSV with blank columns for you to score.
#
#   .\collect_parses.ps1 -Api "https://kairos-api-...run.app"
#
# Output: parses_to_score.csv - open it in Excel and fill the four blank
#         columns by hand. That hand-scoring IS the measurement; there is no
#         way to automate it honestly, because "did it pick the right place"
#         needs a human who knows where Springfield was supposed to be.
#
# REQUIRES the parse_only flag on POST /query (backend/api/query.py). If every
# row comes back with an error mentioning parse_only, the deployed backend
# predates that change - redeploy first.

param(
    [Parameter(Mandatory=$true)][string]$Api,
    [string]$QueryFile = "queries.jsonl",
    [string]$OutDir = "."
)

$ErrorActionPreference = "Continue"

if (-not (Test-Path $QueryFile)) {
    Write-Host "Cannot find $QueryFile - run this from scripts/paper_data/." -ForegroundColor Red
    exit 1
}

$queries = Get-Content $QueryFile | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
Write-Host "Loaded $($queries.Count) test queries.`n" -ForegroundColor Cyan

$rows = @()
foreach ($q in $queries) {
    Write-Host ("[{0,2}/{1}] {2}" -f $q.id, $queries.Count, $q.query) -NoNewline
    $body = @{ query = $q.query; parse_only = $true } | ConvertTo-Json -Compress
    $started = Get-Date
    try {
        $resp = Invoke-RestMethod -Method Post -Uri "$Api/query" `
                    -ContentType "application/json" -Body $body -TimeoutSec 120
        $elapsed = ((Get-Date) - $started).TotalSeconds
        $p = $resp.parameters
        $bboxStr = if ($p.bbox) { ($p.bbox -join ", ") } else { "" }

        $rows += [pscustomobject]@{
            id                = $q.id
            category          = $q.category
            query             = $q.query
            note              = $q.note
            expected_type     = $q.expect_type
            expected_place    = $q.expect_place
            got_understood    = $resp.understood
            got_type          = $p.analysis_type
            got_location      = $p.location_name
            got_bbox          = $bboxStr
            got_start         = $p.start_date
            got_end           = $p.end_date
            got_clarification = $resp.clarification
            got_reasoning     = $p.reasoning
            seconds           = [math]::Round($elapsed, 2)
            # --- fill these in by hand: y / n / na ---
            score_type        = ""
            score_place       = ""
            score_dates       = ""
            score_overall     = ""
            comment           = ""
            error             = ""
        }
        $shown = if ($resp.understood) { "$($p.analysis_type) @ $($p.location_name)" } else { "CLARIFY" }
        Write-Host ("  ->  {0}" -f $shown) -ForegroundColor Green
    }
    catch {
        $rows += [pscustomobject]@{
            id = $q.id; category = $q.category; query = $q.query; note = $q.note
            expected_type = $q.expect_type; expected_place = $q.expect_place
            got_understood = ""; got_type = ""; got_location = ""; got_bbox = ""
            got_start = ""; got_end = ""; got_clarification = ""; got_reasoning = ""
            seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
            score_type = ""; score_place = ""; score_dates = ""; score_overall = ""
            comment = ""; error = $_.Exception.Message
        }
        Write-Host "  ->  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$outPath = Join-Path $OutDir "parses_to_score.csv"
$rows | Export-Csv -Path $outPath -NoTypeInformation -Encoding UTF8

$failed = ($rows | Where-Object { $_.error -ne "" }).Count
$clarified = ($rows | Where-Object { $_.got_understood -eq $false }).Count
$meanSec = [math]::Round((($rows | Measure-Object -Property seconds -Average).Average), 2)

Write-Host "`nWrote $outPath" -ForegroundColor Cyan
Write-Host "  parsed OK        : $($rows.Count - $failed) / $($rows.Count)"
Write-Host "  asked to clarify : $clarified"
Write-Host "  hard errors      : $failed"
Write-Host "  mean parse time  : ${meanSec}s   <- this is your NL-layer latency"
Write-Host @"

NEXT: open parses_to_score.csv and fill score_type / score_place / score_dates
/ score_overall with y, n, or na for each row.

Scoring rules, so the number means something:
  score_type    y if got_type is the right analysis (or correctly CLARIFY/refused
                when expected_type says CLARIFY / REFUSE / AMBIGUOUS_MULTI)
  score_place   y if got_bbox actually contains the intended place. CHECK A FEW
                ON A MAP - a confident bbox in the wrong hemisphere scores n.
  score_dates   y if the window is defensible for the query. For rows 15-21
                (relative dates) this is the interesting column.
  score_overall y only if all three applicable columns are y.

Rows 22-26, 27-31, 32-34 and 39-40 are inverted: asking for clarification or
declining IS the correct answer. Scoring those as failures would understate
the parser; scoring a confident wrong guess as success would overstate it.
"@ -ForegroundColor Yellow
