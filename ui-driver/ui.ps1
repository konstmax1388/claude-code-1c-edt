# ui.ps1 <скрипт.bsl> [-TimeoutSec N]: выполнить скрипт в менеджере тестирования (служебная база tm-base), вывести результат
param([string]$Cmd, [int]$TimeoutSec = 120)
$out = "$Cmd.out"; if ([IO.File]::Exists($out)) { [IO.File]::Delete($out) }
$a = @('ENTERPRISE','/F',(Join-Path $PSScriptRoot 'tm-base'),'/TESTMANAGER','/DisableStartupDialogs','/DisableStartupMessages','/Execute',(Join-Path $PSScriptRoot 'ui_Драйвер.epf'),'/C',"ui=$Cmd|$out")
$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process 'C:\Program Files\1cv8\8.5.1.1507\bin\1cv8c.exe' -ArgumentList $a -PassThru
if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); "TIMEOUT"; exit 2 }
"[$([int]$sw.Elapsed.TotalSeconds) c]"
Get-Content $out -Encoding UTF8 -ErrorAction SilentlyContinue
