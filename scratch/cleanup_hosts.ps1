$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$content = Get-Content $hostsPath
$newContent = $content | Where-Object { $_ -notmatch "dashboard.myflowsgc.shop" }
Set-Content $hostsPath $newContent -Force
ipconfig /flushdns
