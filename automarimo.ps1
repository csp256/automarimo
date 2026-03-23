param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsForAutomarimo
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Automarimo = Join-Path $ScriptDir 'automarimo.py'

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -3 $Automarimo @ArgsForAutomarimo
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $Automarimo @ArgsForAutomarimo
    exit $LASTEXITCODE
}

$python3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($python3) {
    & $python3.Source $Automarimo @ArgsForAutomarimo
    exit $LASTEXITCODE
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    & $uv.Source run $Automarimo @ArgsForAutomarimo
    exit $LASTEXITCODE
}

Write-Host "Python or uv was not found. Please install Python 3.11+ or uv first."
Read-Host "Press Enter to continue"
exit 1