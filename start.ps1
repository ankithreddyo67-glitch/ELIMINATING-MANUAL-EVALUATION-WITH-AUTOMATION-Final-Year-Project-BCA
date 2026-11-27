$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        & python --version *> $null
        if ($LASTEXITCODE -eq 0) { $pythonCmd = "python" }
    } catch {}
}
if (-not $pythonCmd -and (Test-Path "C:\Program Files\Thonny\python.exe")) {
    $pythonCmd = "C:\Program Files\Thonny\python.exe"
}
if (-not $pythonCmd) {
    Write-Error "Python 3.10+ interpreter not found."
    exit 1
}

Write-Host "Starting AutoExam AI using $pythonCmd ..."
& $pythonCmd app.py
