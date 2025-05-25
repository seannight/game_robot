# Port Checker Script - ASCII Version

# Set console code page to UTF-8
chcp 65001 | Out-Null

# Set terminal encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Fixed port setting
$PORT = 53085

# Check if port is in use
function Test-PortInUse($Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return ($null -ne $connections)
}

# Check if port is occupied
if (Test-PortInUse -Port $PORT) {
    Write-Host "WARNING: Port $PORT is already in use!" -ForegroundColor Red
    
    $tryPort = $PORT + 1
    while (Test-PortInUse -Port $tryPort -and $tryPort -lt ($PORT + 20)) {
        $tryPort++
    }
    
    if ($tryPort -lt ($PORT + 20)) {
        Write-Host "Automatically using alternative port: $tryPort" -ForegroundColor Yellow
        $PORT = $tryPort
    } else {
        Write-Host "Unable to find available port" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Using port: $PORT" -ForegroundColor Green
return $PORT 