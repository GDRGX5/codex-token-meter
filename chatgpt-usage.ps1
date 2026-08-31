$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'chatgpt_usage.py'

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    Write-Error "找不到主程式：$scriptPath`n請確認 chatgpt-usage.ps1 和 chatgpt_usage.py 位於同一資料夾，且檔名沒有多餘的反斜線。"
    exit 2
}

$launchers = @(
    [pscustomobject]@{ Name = 'python';  PrefixArgs = @() },
    [pscustomobject]@{ Name = 'python3'; PrefixArgs = @() },
    [pscustomobject]@{ Name = 'py';      PrefixArgs = @('-3') }
)

foreach ($launcher in $launchers) {
    $command = Get-Command $launcher.Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $command) {
        continue
    }

    $prefixArgs = @($launcher.PrefixArgs)
    $majorVersion = & $command.Source @prefixArgs -c 'import sys; print(sys.version_info.major)' 2>$null
    if ($LASTEXITCODE -eq 0 -and $majorVersion[-1] -eq '3') {
        & $command.Source @prefixArgs $scriptPath @args
        exit $LASTEXITCODE
    }
}

# Python 已安裝但沒有加入 PATH 時，嘗試 Windows 使用者層級的常見安裝位置。
$localPrograms = Join-Path $env:LOCALAPPDATA 'Programs\Python'
if (Test-Path -LiteralPath $localPrograms -PathType Container) {
    $installedPythons = Get-ChildItem -Path (Join-Path $localPrograms 'Python*\python.exe') -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    foreach ($pythonExe in $installedPythons) {
        $majorVersion = & $pythonExe.FullName -c 'import sys; print(sys.version_info.major)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $majorVersion[-1] -eq '3') {
            & $pythonExe.FullName $scriptPath @args
            exit $LASTEXITCODE
        }
    }
}

Write-Error @'
Python 可能已安裝，但目前的 PowerShell 找不到可執行的 Python 3。
請執行下列指令檢查終端機實際能看到的路徑：
  Get-Command python, python3, py -ErrorAction SilentlyContinue

也可以直接執行同資料夾內的 chatgpt-usage.cmd。
'@
exit 1
