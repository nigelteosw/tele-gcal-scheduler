# Stop on error
$ErrorActionPreference = "Stop"

Write-Host "Cleaning build directory..."
Remove-Item -Recurse -Force .\lambda_package -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path .\lambda_package | Out-Null

Write-Host "Installing dependencies..."
pip install -r requirements.txt -t .\lambda_package

Write-Host "Copying source files..."
Copy-Item .\bot.py .\lambda_package\
Copy-Item .\creds.json .\lambda_package\  # optional – remove if not needed

Write-Host "Zipping contents..."
Compress-Archive -Path .\lambda_package\* -DestinationPath .\lambda-deploy.zip -Force

Write-Host "lambda-deploy.zip is ready!"
