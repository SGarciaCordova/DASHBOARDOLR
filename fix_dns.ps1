if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$domain = "dashboard.myflowsgc.shop"
$ip = "104.21.50.175"
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$entry = "$ip $domain"

try {
    if (Select-String -Path $hostsPath -Pattern $domain -Quiet) {
        Write-Host "La entrada ya existe en el archivo hosts." -ForegroundColor Yellow
    }
    else {
        Add-Content -Path $hostsPath -Value "`r`n$entry" -Force
        Write-Host "Exito! Se agrego: $entry" -ForegroundColor Green
    }
    ipconfig /flushdns
    Write-Host "DNS cache vaciada." -ForegroundColor Green
}
catch {
    Write-Error "Error: $_"
    Read-Host "Error. Presiona Enter..."
}

Read-Host "Presiona Enter para cerrar..."
