$path = $PSScriptRoot
Set-Location $path

Write-Host "Iniciando Dashboard..." -ForegroundColor Green
Start-Process streamlit -ArgumentList "run Dashboard.py --server.port 8501 --server.address 0.0.0.0" -WindowStyle Minimized

# Túnel Cloudflare activado — Acceso externo automático
Start-Sleep -Seconds 5
Start-Process .\cloudflared.exe -ArgumentList "tunnel run dashboard-sgc" -WindowStyle Minimized

