# One-command build for the SPSS/PSPP t-test module.
# Run:  powershell -ExecutionPolicy Bypass -File WEEK5/build/build.ps1
$ErrorActionPreference = 'Stop'

$build = Split-Path -Parent $MyInvocation.MyCommand.Path
$week5 = Split-Path -Parent $build
$handoutDocx = Join-Path $week5 'Week5_SPSS_Ttest_Practice.docx'
$handoutPdf  = Join-Path $week5 'Week5_SPSS_Ttest_Practice.pdf'

function Invoke-Step {
    param([string]$Label, [string]$Exe, [string[]]$StepArgs)
    Write-Host "=== $Label ==="
    & $Exe @StepArgs
    if ($LASTEXITCODE -ne 0) { Write-Host "BUILD FAILED at: $Label"; exit 1 }
}

foreach ($s in 'make_sav.py', 'test_make_sav.py', 'test_pspp_parse.py', 'run_and_check.py', 'test_run_and_check.py') {
    # run_and_check.py computes every answer, so it lives only in the private repo; the public repo
    # ships a trimmed expected_results.json instead (see make_public.py)
    if ($s -like '*run_and_check.py' -and -not (Test-Path (Join-Path $build $s))) {
        Write-Host "=== $s not present: using the shipped expected_results.json ==="
        continue
    }
    Invoke-Step $s 'python' @((Join-Path $build $s))
}

# Quarto needs a Python with PyYAML (system Python lacks it)
$env:QUARTO_PYTHON = 'C:/Users/xiada/anaconda3/python.exe'
Push-Location $build
try {
    Invoke-Step 'quarto render handout.qmd' 'quarto' @('render', 'handout.qmd', '--output-dir', '..')
    # The answer key lives only in the private repo; the public repo builds the handout alone
    if (Test-Path (Join-Path $build 'answer_key.qmd')) {
        Invoke-Step 'quarto render answer_key.qmd' 'quarto' @('render', 'answer_key.qmd', '--output-dir', '..')
    } else {
        Write-Host '=== answer_key.qmd not present: skipping the answer key ==='
    }
}
finally { Pop-Location }

Invoke-Step 'check_docs.py' 'python' @((Join-Path $build 'check_docs.py'))

Write-Host '=== Word COM: handout to PDF ==='
if (Test-Path $handoutPdf) { Remove-Item $handoutPdf }
# Convert a temp copy (avoids a file lock from the user's own Word) in a background job
# with a hard timeout. The job only ever touches a Word instance that it proves it created
# itself (exactly one new WINWORD PID, no open documents); it never alters or quits any other Word.
$tmpDir = Join-Path ([IO.Path]::GetTempPath()) ('week5_pdf_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$tmpDocx = Join-Path $tmpDir 'handout.docx'
$tmpPdf  = Join-Path $tmpDir 'handout.pdf'
$pidFile = Join-Path $tmpDir 'word.pid'
$failMsg = $null
try {
    Copy-Item $handoutDocx $tmpDocx
    $job = Start-Job -ScriptBlock {
        param($docxPath, $pdfPath, $pidPath)
        $ErrorActionPreference = 'Stop'
        $before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
        $word = New-Object -ComObject Word.Application
        $after = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
        $new = @($after | Where-Object { $before -notcontains $_ })
        if ($new.Count -ne 1) {
            # Not provably our own instance: touch nothing (no DisplayAlerts, no Quit)
            throw "Could not confirm a private Word instance (new WINWORD PIDs: $($new.Count)); left Word untouched"
        }
        Set-Content -Path $pidPath -Value $new[0]
        $doc = $null
        try {
            if ($word.Documents.Count -ne 0) { throw 'New Word instance already has documents open' }
            $word.Visible = $false
            $word.DisplayAlerts = 0
            $doc = $word.Documents.Open($docxPath, $false, $true)
            $doc.SaveAs2($pdfPath, 17)
            $doc.Close($false)
            $doc = $null
        }
        finally {
            try { if ($doc -ne $null) { $doc.Close($false) } }
            finally { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
        }
    } -ArgumentList $tmpDocx, $tmpPdf, $pidFile
    if (-not (Wait-Job $job -Timeout 120)) {
        # Kill the recorded private Word first (Stop-Job can block on a stuck COM call)
        if (Test-Path $pidFile) {
            $wp = [int](Get-Content $pidFile)
            Stop-Process -Id $wp -Force
            $failMsg = "Word conversion timed out after 120 s; killed the build's own hidden Word (PID $wp)"
        } else {
            $failMsg = 'Word conversion timed out after 120 s and no private Word PID was recorded; nothing was killed. Close any stray hidden WINWORD.EXE manually'
        }
        Stop-Job $job
        Remove-Job $job -Force
    } else {
        if ($job.State -ne 'Completed') {
            $reason = ($job.ChildJobs[0].JobStateInfo.Reason | Out-String).Trim()
            $failMsg = "Word job state $($job.State): $reason"
        } else {
            Receive-Job $job | Out-Null
        }
        Remove-Job $job -Force
    }
    if ($null -eq $failMsg) {
        if (-not (Test-Path $tmpPdf)) { $failMsg = 'PDF not produced' }
        else { Move-Item $tmpPdf $handoutPdf }
    }
}
finally { Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue }
if ($null -ne $failMsg) { Write-Host "BUILD FAILED: $failMsg"; exit 1 }

if (-not (Test-Path $handoutPdf)) { Write-Host 'BUILD FAILED: PDF missing'; exit 1 }
if ((Get-Item $handoutPdf).Length -le 0) { Write-Host 'BUILD FAILED: PDF is empty'; exit 1 }
# Spec 6: the PDF must have at least one page
$pages = & python -c "import sys, pypdf; n = len(pypdf.PdfReader(sys.argv[1]).pages); print(n); sys.exit(0 if n > 0 else 1)" $handoutPdf
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD FAILED: PDF has no pages or cannot be read ($pages)"; exit 1 }
Write-Host ("PDF OK: {0} ({1} bytes, {2} pages)" -f $handoutPdf, (Get-Item $handoutPdf).Length, $pages)
Write-Host 'BUILD PASSED'
