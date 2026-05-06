# Integrated Softphone Installation Script for Windows
# Run this in PowerShell to install the softphone

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Integrated Softphone Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Step 1: Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check pip
Write-Host "Step 2: Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "✓ pip found: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ pip not found!" -ForegroundColor Red
    Write-Host "Please install pip" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install PyAudio
Write-Host "Step 3: Installing PyAudio..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray

try {
    pip install pyaudio 2>&1 | Out-Null
    Write-Host "✓ PyAudio installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠ PyAudio installation failed with pip" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Trying alternative method..." -ForegroundColor Yellow
    Write-Host "Downloading pre-built wheel..." -ForegroundColor Gray
    
    # Detect Python version
    $pythonVersionMatch = python --version 2>&1 | Select-String -Pattern "Python (\d+)\.(\d+)"
    if ($pythonVersionMatch) {
        $majorVersion = $pythonVersionMatch.Matches.Groups[1].Value
        $minorVersion = $pythonVersionMatch.Matches.Groups[2].Value
        $pythonVer = "cp$majorVersion$minorVersion"
        
        Write-Host "Detected Python version: $majorVersion.$minorVersion" -ForegroundColor Gray
        
        # Download appropriate wheel
        $wheelUrl = "https://download.lfd.uci.edu/pythonlibs/archived/PyAudio-0.2.11-$pythonVer-$pythonVer-win_amd64.whl"
        $wheelFile = "$env:TEMP\PyAudio-0.2.11-$pythonVer-$pythonVer-win_amd64.whl"
        
        try {
            Invoke-WebRequest -Uri $wheelUrl -OutFile $wheelFile -ErrorAction Stop
            pip install $wheelFile
            Write-Host "✓ PyAudio installed from wheel!" -ForegroundColor Green
        } catch {
            Write-Host "✗ Could not download wheel automatically" -ForegroundColor Red
            Write-Host ""
            Write-Host "Manual installation required:" -ForegroundColor Yellow
            Write-Host "1. Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor White
            Write-Host "2. Download the .whl file for Python $majorVersion.$minorVersion" -ForegroundColor White
            Write-Host "3. Run: pip install <downloaded-file>.whl" -ForegroundColor White
            exit 1
        }
    }
}

Write-Host ""

# Install other requirements
Write-Host "Step 4: Installing other requirements..." -ForegroundColor Yellow
try {
    pip install requests twilio 2>&1 | Out-Null
    Write-Host "✓ All requirements installed!" -ForegroundColor Green
} catch {
    Write-Host "⚠ Some requirements failed to install" -ForegroundColor Yellow
}

Write-Host ""

# Verify installation
Write-Host "Step 5: Verifying installation..." -ForegroundColor Yellow
try {
    python -c "import pyaudio; print('PyAudio OK')" 2>&1 | Out-Null
    Write-Host "✓ PyAudio verified!" -ForegroundColor Green
} catch {
    Write-Host "✗ PyAudio verification failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: python desktop_app.py" -ForegroundColor White
Write-Host "2. Go to the 'Softphone' tab" -ForegroundColor White
Write-Host "3. Click 'Launch Softphone' for each agent" -ForegroundColor White
Write-Host ""
Write-Host "For help, see: SOFTPHONE_SETUP.md" -ForegroundColor Gray
Write-Host ""
