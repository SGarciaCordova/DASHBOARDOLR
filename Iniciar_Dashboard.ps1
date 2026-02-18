$path = "c:\Users\Usuario1\Desktop\Antigravity SGC"
Set-Location $path

Write-Host "Iniciando Dashboard..." -ForegroundColor Green
Start-Process streamlit -ArgumentList "run Dashboard.py --server.port 8501 --server.address 127.0.0.1" -WindowStyle Minimized

Start-Sleep -Seconds 5

Write-Host "Iniciando Túnel..." -ForegroundColor Green
Start-Process .\cloudflared.exe -ArgumentList "tunnel run dashboard-sgc" -WindowStyle Minimized
