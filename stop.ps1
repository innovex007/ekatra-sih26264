# Stops whatever is listening on Ekatra's ports (API 8010, UI 5174), including orphaned reload workers.
$ports = 8010, 5174
$pids = @()
foreach ($port in $ports) {
    netstat -ano | Select-String "[:\]]$port\s+\S+\s+LISTENING\s+(\d+)" | ForEach-Object { $pids += [int]$_.Matches[0].Groups[1].Value }
}
$pids = $pids | Sort-Object -Unique | Where-Object { $_ -gt 0 }
if (-not $pids) { Write-Host "Nothing is listening on ports $($ports -join ', ')." -ForegroundColor Green; exit 0 }
foreach ($id in $pids) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
    Write-Host "Stopping PID $id $($p.Name)" -ForegroundColor Yellow
    taskkill /PID $id /T /F | Out-Null
}
Write-Host "Stopped. Ports are free." -ForegroundColor Green
