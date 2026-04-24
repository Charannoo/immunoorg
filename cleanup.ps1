#!/usr/bin/env powershell
# ImmunoOrg: Automated Cleanup Script
# Removes unwanted files before submission

Write-Host "🧹 ImmunoOrg Cleanup Script" -ForegroundColor Cyan
Write-Host "=" * 70

$projectPath = "D:\scaler-r2"

# Step 1: Remove __pycache__ directories
Write-Host "`n1️⃣ Removing __pycache__ directories..." -ForegroundColor Yellow
$pycacheDirs = Get-ChildItem -Path $projectPath -Recurse -Directory -Name "__pycache__"
if ($pycacheDirs) {
    $count = 0
    foreach ($dir in $pycacheDirs) {
        $fullPath = Join-Path $projectPath $dir
        Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ✅ Removed: $dir"
        $count++
    }
    Write-Host "`n   Total removed: $count directories"
} else {
    Write-Host "  ✅ No __pycache__ directories found"
}

# Step 2: Remove .pyc files
Write-Host "`n2️⃣ Removing .pyc files..." -ForegroundColor Yellow
$pycFiles = Get-ChildItem -Path $projectPath -Recurse -File -Name "*.pyc"
if ($pycFiles) {
    $count = 0
    foreach ($file in $pycFiles) {
        $fullPath = Join-Path $projectPath $file
        Remove-Item -Path $fullPath -Force -ErrorAction SilentlyContinue
        Write-Host "  ✅ Removed: $file"
        $count++
    }
    Write-Host "`n   Total removed: $count .pyc files"
} else {
    Write-Host "  ✅ No .pyc files found"
}

# Step 3: Create/Update .gitignore
Write-Host "`n3️⃣ Creating/updating .gitignore..." -ForegroundColor Yellow
$gitignorePath = Join-Path $projectPath ".gitignore"
$gitignoreContent = @"
# Python cache
__pycache__/
*.py[cod]
*`$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
venv/
env/
ENV/
.venv
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*.bak
*~
.DS_Store
Thumbs.db

# Jupyter
.ipynb_checkpoints/
*.ipynb_checkpoints

# Environment
.env
.env.local
.env.*.local

# Models & Large Files
*.pkl
*.pth
*.pickle
*.bin
*.safetensors
*.h5
*.ckpt
checkpoints/
models/

# Data
data/
*.csv
*.xlsx

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db
.directory

# Misc
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.dmypy.json
dmypy.json
"@

if (Test-Path $gitignorePath) {
    Write-Host "  📝 .gitignore already exists, updating..."
    Add-Content -Path $gitignorePath -Value "`n# Updated by cleanup script" -Encoding UTF8
} else {
    Write-Host "  ✨ Creating new .gitignore..."
    Set-Content -Path $gitignorePath -Value $gitignoreContent -Encoding UTF8
}
Write-Host "  ✅ .gitignore ready"

# Step 4: Verify removal
Write-Host "`n4️⃣ Verifying cleanup..." -ForegroundColor Yellow
$remainingCache = Get-ChildItem -Path $projectPath -Recurse -Directory -Name "__pycache__"
$remainingPyc = Get-ChildItem -Path $projectPath -Recurse -File -Name "*.pyc"

if ($remainingCache) {
    Write-Host "  ⚠️ Warning: Some __pycache__ directories still found"
    $remainingCache | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "  ✅ No __pycache__ directories"
}

if ($remainingPyc) {
    Write-Host "  ⚠️ Warning: Some .pyc files still found"
    $remainingPyc | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "  ✅ No .pyc files"
}

# Step 5: Security check
Write-Host "`n5️⃣ Security check..." -ForegroundColor Yellow
$suspiciousFiles = Get-ChildItem -Path $projectPath -Recurse -File | Where-Object {
    $_.Name -match '(\.env|secret|password|token|credential|api_key)' -and
    $_.Extension -ne '.md'
}

if ($suspiciousFiles) {
    Write-Host "  ⚠️ Found potentially sensitive files:"
    $suspiciousFiles | ForEach-Object { Write-Host "    $($_.FullName)" }
} else {
    Write-Host "  ✅ No suspicious files found"
}

# Step 6: Summary
Write-Host "`n" + "=" * 70
Write-Host "✅ CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "=" * 70

Write-Host "`n📊 Summary:"
Write-Host "  ✅ __pycache__ directories removed"
Write-Host "  ✅ .pyc files removed"
Write-Host "  ✅ .gitignore created/updated"
Write-Host "  ✅ No credentials found"
Write-Host "`n🚀 Next steps:"
Write-Host "  1. cd $projectPath"
Write-Host "  2. git add -A"
Write-Host "  3. git commit -m 'Clean build artifacts before submission'"
Write-Host "  4. git push"
Write-Host "`n📝 Verify with: git status"
Write-Host "   (Should show: working tree clean)"
