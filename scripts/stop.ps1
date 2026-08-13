# Stop and remove the app container. Windows.
docker rm -f pm-app 2>$null | Out-Null
Write-Output "Stopped."
