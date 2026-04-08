echo "Starting cleanup..." > "c:\Users\Usuario1\Desktop\Antigravity SGC\scratch\cleanup_log.txt"
$path = "C:\Windows\System32\drivers\etc\hosts"
$content = Get-Content $path
$countBefore = $content.Count
echo "Lines before: $countBefore" >> "c:\Users\Usuario1\Desktop\Antigravity SGC\scratch\cleanup_log.txt"
$newContent = $content | Where-Object { $_ -notmatch "dashboard.myflowsgc.shop" }
$countAfter = $newContent.Count
echo "Lines after: $countAfter" >> "c:\Users\Usuario1\Desktop\Antigravity SGC\scratch\cleanup_log.txt"
$newContent | Set-Content $path -Force
echo "File written." >> "c:\Users\Usuario1\Desktop\Antigravity SGC\scratch\cleanup_log.txt"
ipconfig /flushdns
echo "DNS flushed." >> "c:\Users\Usuario1\Desktop\Antigravity SGC\scratch\cleanup_log.txt"
