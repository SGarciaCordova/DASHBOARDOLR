if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ip = "192.168.100.242"
$prefixLength = 24
$gateway = "192.168.100.1"
$dns = "8.8.8.8"

# Buscar el adaptador que actualmente tiene la IP del rango 192.168.100.x o que se llama Ethernet/Wi-Fi
$adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and ($_.Name -like '*Ethernet*' -or $_.Name -like '*Wi-Fi*') } | Select-Object -First 1

if ($adapter) {
    Write-Host "Configurando el adaptador: $($adapter.Name) con la IP: $ip" -ForegroundColor Cyan
    
    # Remover IP actual (en caso de que estuviera fija de otro lado) o deshabilitar DHCP
    Set-NetIPInterface -InterfaceAlias $adapter.Name -Dhcp Disabled
    
    # Configurar la nueva IP Fija
    New-NetIPAddress -InterfaceAlias $adapter.Name -IPAddress $ip -PrefixLength $prefixLength -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
    Set-NetIPAddress -InterfaceAlias $adapter.Name -IPAddress $ip -PrefixLength $prefixLength -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
    
    # Configurar DNS
    Set-DnsClientServerAddress -InterfaceAlias $adapter.Name -ServerAddresses $dns
    
    Write-Host "Configuracion de IP Estatica completada. IP fijada a $ip" -ForegroundColor Green
} else {
    Write-Host "No se encontro un adaptador activo." -ForegroundColor Red
}

Read-Host "Presiona Enter para cerrar..."
